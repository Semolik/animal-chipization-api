from datetime import datetime
from typing import List, Union

from fastapi import HTTPException
from sqlalchemy import func, or_, and_, distinct, select, literal_column, case, exists, not_
from sqlalchemy.orm import aliased, subqueryload

from app.crud.base import CRUDBase
from app.models.animals import Animal, AnimalLocation, AnimalType, AnimalTypeAnimal
from app.models.areas import Area, AreaPoint
from app.models.points import Point
from app.schemas.locations import LocationBase

class AreaCRUD(CRUDBase):
    def create_area(self, name: str, points: list[LocationBase]) -> Area:
        area = self.create(Area(name=name))
        return self.create_area_points(area, points)

    def create_area_points(self, area: Area, points: list[LocationBase]) -> Area:
        first_point = self.create(
            AreaPoint(area_id=area.id, latitude=points[0].latitude, longitude=points[0].longitude))
        prev_point = first_point
        for point in points[1:]:
            current_point = self.create(AreaPoint(area_id=area.id, latitude=point.latitude, longitude=point.longitude))
            prev_point.next_id = current_point.id
            self.update(prev_point)
            prev_point = current_point
        prev_point.next_id = first_point.id
        self.update(prev_point)
        return area

    def get_area(self, area_id: int) -> Area | None:
        return self.get(area_id, Area)

    def update_area(self, db_area: Area, name: str, points: List[LocationBase]) -> Area:
        db_area.name = name
        for point in db_area.areaPoints:
            self.delete(point)
        return self.create_area_points(db_area, points)

    def area_by_points(self, points: list[LocationBase]) -> Area | None:
        '''Проверяет, существует ли зона, состоящая из таких точек'''
        query = (
            self.db.query(Area)
            .join(AreaPoint)
            .filter(
                and_(
                    AreaPoint.latitude == points[0].latitude,
                    AreaPoint.longitude == points[0].longitude
                )
            )
        )
        for i in range(1, len(points)):
            subquery = (
                self.db.query(AreaPoint.area_id)
                .filter(
                    and_(
                        AreaPoint.latitude == points[i].latitude,
                        AreaPoint.longitude == points[i].longitude
                    )
                )
            )
            query = query.filter(Area.id.in_(subquery))
        count = query.group_by(Area.id).having(func.count(Area.id) == len(points)).count()
        return query.first() if count > 0 else None
    def _get_next_point_and_current_point_subquery(self):
        return (
            self.db.query(
                AreaPoint.id.label("id"), AreaPoint.latitude.label("latitude"),
                AreaPoint.longitude.label("longitude"),
                (
                    self.db.query(
                        AreaPoint.latitude
                    )
                    .filter(AreaPoint.id == AreaPoint.next_id)
                    .as_scalar()
                ).label("next_latitude"),
                (
                    self.db.query(
                        AreaPoint.longitude
                    )
                    .filter(AreaPoint.id == AreaPoint.next_id)
                    .as_scalar()
                ).label("next_longitude"),
                Area.id.label("area_id")
            )
            .subquery()
        )

    def new_area_is_correct(self, points: list[LocationBase], only_intersects: bool = False) -> bool:
        subquery = self._get_next_point_and_current_point_subquery()
        intersection_filter = self._get_intersection_filter(points, subquery)
        query = self.db.query(Area).join(AreaPoint).join(subquery, subquery.c.id == AreaPoint.id)
        if only_intersects:
            query = query.filter(intersection_filter)
            return query.first() is None
        else:
            filters = {
                "intersection": intersection_filter,
                "containment": self._get_containment_filter(points, subquery),
                "new_area_inside": self._get_new_area_inside_filter(points, subquery)
            }
            for filter_name, filter in filters.items():
                error_area = query.filter(filter).first()
                #print(f"New area points: {points}")

                if error_area is not None:
                    msg =f"New area intersects with {filter_name} area {error_area.id}"
                    #print(msg)
                    # print(
                    #     f"Error area points: {[(point.latitude, point.longitude) for point in error_area.areaPoints]}")
                    raise HTTPException(status_code=400, detail=msg)
            return True

    def _get_intersection_filter(self, points, subquery):
        filters = []
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                p1 = points[i]
                p2 = points[j]
                min_lat = min(p1.latitude, p2.latitude)
                max_lat = max(p1.latitude, p2.latitude)
                min_long = min(p1.longitude, p2.longitude)
                max_long = max(p1.longitude, p2.longitude)
                filters.append(
                    and_(
                        subquery.c.latitude <= max_lat,
                        subquery.c.next_latitude >= min_lat,
                        subquery.c.longitude <= max_long,
                        subquery.c.next_longitude >= min_long,
                        or_(
                            and_(
                                subquery.c.latitude >= p1.latitude,
                                subquery.c.next_latitude >= p1.latitude,
                                subquery.c.latitude <= p2.latitude,
                                subquery.c.next_latitude <= p2.latitude,
                                subquery.c.longitude <= p1.longitude,
                                subquery.c.next_longitude >= p2.longitude,

                            ),
                            and_(
                                subquery.c.latitude >= p2.latitude,
                                subquery.c.next_latitude >= p2.latitude,
                                subquery.c.latitude <= p1.latitude,
                                subquery.c.next_latitude <= p1.latitude,
                                subquery.c.longitude <= p2.longitude,
                                subquery.c.next_longitude >= p1.longitude,

                            ),
                            and_(
                                subquery.c.latitude >= p1.latitude,
                                subquery.c.next_latitude <= p2.latitude,
                                subquery.c.longitude <= p1.longitude,
                                subquery.c.next_longitude >= p2.longitude,

                            ),
                            and_(
                                subquery.c.latitude >= p2.latitude,
                                subquery.c.next_latitude <= p1.latitude,
                                subquery.c.longitude <= p2.longitude,
                                subquery.c.next_longitude >= p1.longitude,
                            ),
                        )
                    )
                )
        return or_(*filters)



    def _get_containment_filter(self, points: List[LocationBase], subquery):
        '''Проверяет, что новая зона содержится внутри существующих'''
        filters = []
        for i, point in enumerate(points[:-1]):
            next_point = points[i + 1]
            if next_point.longitude - point.longitude != 0:
                k = (next_point.latitude - point.latitude) / (next_point.longitude - point.longitude)
                b = point.latitude - k * point.longitude
                filters.append(
                    and_(
                        subquery.c.latitude >= k * subquery.c.longitude + b,
                        subquery.c.next_latitude >= k * subquery.c.next_longitude + b
                    )
                )
            else:
                filters.append(
                    and_(
                        subquery.c.longitude == point.longitude,
                        subquery.c.latitude >= point.latitude,
                        subquery.c.next_longitude == point.longitude,
                        subquery.c.next_latitude >= point.latitude,
                    )
                )
        return or_(*filters)

    def _get_new_area_inside_filter(self, points: List[LocationBase], subquery):
        filters = []
        for i, point in enumerate(points[:-1]):
            next_point = points[i + 1]
            if next_point.longitude - point.longitude != 0:
                k = (next_point.latitude - point.latitude) / (next_point.longitude - point.longitude)
                b = point.latitude - k * point.longitude
                filters.append(
                    and_(
                        subquery.c.latitude <= k * subquery.c.longitude + b,
                        subquery.c.next_latitude <= k * subquery.c.next_longitude + b
                    )
                )
            else:
                filters.append(
                    and_(
                        subquery.c.longitude == point.longitude,
                        subquery.c.latitude <= point.latitude,
                        subquery.c.next_longitude == point.longitude,
                        subquery.c.next_latitude >= next_point.latitude,
                    )
                )
        return or_(*filters)




    def get_area_by_name(self, name: str) -> Area | None:
        return self.db.query(Area).filter(Area.name == name).first()

    def get_area_analytics(self, area_id: int, start_date: datetime, end_date: datetime):
        query = (
            self._get_analytics_query(
                area_id=area_id,
                start_date=start_date,
                end_date=end_date,
                query=self.db.query(
                    AnimalType.type.label("animalType"),
                    AnimalType.id.label("animalTypeId"),
                )
            )
            .group_by(AnimalType.id)
        )
        info = []
        for animal_type in query:
            type_query = (self._get_analytics_query(
                        area_id=area_id,
                        start_date=start_date,
                        end_date=end_date,
                        query=self.db.query(
                            Animal.id
                        )
                    )
                    .filter(AnimalType.id == animal_type.animalTypeId)
                    .distinct(Animal.id))
            print("type_query", type_query.all())
            info.append(
                {
                    "animalType": animal_type.animalType,
                    "animalTypeId": animal_type.animalTypeId,
                    "animalsArrived": self.get_area_analytics_animals_arrived(area_id, start_date, end_date, type_id=animal_type.animalTypeId),
                    "animalsGone": self.get_area_analytics_animals_gone(area_id, start_date, end_date, type_id=animal_type.animalTypeId),
                    "quantityAnimals": type_query.count(),
                }
            )
        return info

    def get_area_analytics_animals_count(self, area_id: int, start_date: datetime, end_date: datetime):
        query = (
            self._get_analytics_query(
                area_id=area_id,
                start_date=start_date,
                end_date=end_date,
                query=self.db.query(
                    Animal.id
                )
            )
            .distinct(Animal.id)
        )
        return query.count()

    def get_area_analytics_animals_arrived(self, area_id: int, start_date: datetime, end_date: datetime, type_id: int = None):
        query = self._get_analytics_query(
            area_id=area_id,
            start_date=start_date,
            end_date=end_date,
            query=self.db.query(
                Animal.id, AnimalLocation.dateTimeOfVisitLocationPoint, Point.id, Animal.chippingLocationId, AnimalLocation.id
            )
        ).order_by(Animal.id, AnimalLocation.dateTimeOfVisitLocationPoint.asc()).distinct(Animal.id)
        if type_id is not None:
            query = query.filter(AnimalType.id == type_id)
        arrived = 0
        area_points = self.db.query(Point).join(AreaPoint, AreaPoint.area_id == area_id).all()
        for animal_id, date, current_point_id, chipping_location_id, animal_location_id in query.all():
            prev_location_point = self.db.query(Point).join(AnimalLocation, AnimalLocation.locationPointId == Point.id).filter(
                AnimalLocation.animalId == animal_id,
                AnimalLocation.dateTimeOfVisitLocationPoint < date
            ).order_by(AnimalLocation.dateTimeOfVisitLocationPoint.desc()).first()

            if prev_location_point is None and chipping_location_id <= current_point_id:
                prev_location_point = self.db.query(Point).filter(Point.id == chipping_location_id).first()
            print("Текущая точка:", current_point_id)
            print("Предыдущая точка:", prev_location_point.id if prev_location_point else None)
            print("Точка чипирования:", chipping_location_id)
            print()
            if prev_location_point is not None:
                is_in_area = True
                for point in area_points:
                    if not (point.latitude <= prev_location_point.latitude and
                        (prev_location_point.longitude - point.longitude) * (point.latitude - prev_location_point.latitude)
                        >= (point.longitude - prev_location_point.longitude) * (prev_location_point.latitude - point.latitude)):
                        is_in_area = False
                        break
                if is_in_area:
                    arrived += 1
                print("Предыдущая точка в зоне:", is_in_area)
        return arrived

    def get_area_analytics_animals_gone(self, area_id: int, start_date: datetime, end_date: datetime, type_id: int= None):
        query = self._get_analytics_query(
            area_id=area_id,
            start_date=start_date,
            end_date=end_date,
            query=self.db.query(
                Animal.id, AnimalLocation.dateTimeOfVisitLocationPoint, Point.id, Animal.chippingLocationId,
                AnimalLocation.id
            ),
        ).order_by(Animal.id, AnimalLocation.dateTimeOfVisitLocationPoint.asc()).distinct(Animal.id)
        if type_id is not None:
            query = query.filter(AnimalType.id == type_id)
        gone = 0
        area_points = self.db.query(Point).join(AreaPoint, AreaPoint.area_id == area_id).all()
        for animal_id, date, current_point_id, chipping_location_id, animal_location_id in query.all():
            next_location_point = self.db.query(Point).join(AnimalLocation, AnimalLocation.locationPointId == Point.id).filter(
                AnimalLocation.animalId == animal_id,
                AnimalLocation.dateTimeOfVisitLocationPoint > date
            ).order_by(AnimalLocation.dateTimeOfVisitLocationPoint.asc()).first()
            print("Текущая точка:", current_point_id)
            print("Следующая точка:", next_location_point.id if next_location_point else None)
            print("Координаты следующей точки:", (next_location_point.latitude, next_location_point.longitude) if next_location_point else "None")
            print("Координаты зоны:", [(point.latitude, point.longitude) for point in area_points] )
            print("Точка чипирования:", chipping_location_id)
            print()
            if not next_location_point:
                next_location_point = self.db.query(Point).filter(Point.id == current_point_id).first()
            if next_location_point is not None:
                is_in_area = True
                for point in area_points:
                    if not (point.latitude <= next_location_point.latitude and
                        (next_location_point.longitude - point.longitude) * (point.latitude - next_location_point.latitude)
                        >= (point.longitude - next_location_point.longitude) * (next_location_point.latitude - point.latitude)):
                        is_in_area = False
                        break
                if not is_in_area:
                    gone += 1
                print("Следующая точка в зоне:", is_in_area is None)
        return gone

    def get_next_animal_location(self, animal_id: int, date_time: datetime):
        return (
            self.db.query(AnimalLocation)
            .filter(AnimalLocation.animalId == animal_id)
            .filter(AnimalLocation.dateTimeOfVisitLocationPoint > date_time)
            .order_by(AnimalLocation.dateTimeOfVisitLocationPoint)
            .first()
        )

    def _get_analytics_query(self, area_id: int, query, start_date: datetime = None, end_date: datetime = None):
        query = (
            query
            .select_from(AnimalLocation)
            .join(Animal, Animal.id == AnimalLocation.animalId)
            .join(AnimalTypeAnimal, AnimalTypeAnimal.animal_id == Animal.id)
            .join(AnimalType, AnimalType.id == AnimalTypeAnimal.type_id)
            .join(Point, or_(Point.id == AnimalLocation.locationPointId, Point.id == Animal.chippingLocationId))
            .join(Area, Area.id == area_id)
            .join(AreaPoint)
            .filter(
                AreaPoint.latitude <= Point.latitude,
                (Point.longitude - AreaPoint.longitude) * (AreaPoint.latitude - Point.latitude)
                >= (AreaPoint.longitude - Point.longitude) * (Point.latitude - AreaPoint.latitude),
            ))
        if start_date:
            query = query.filter(AnimalLocation.dateTimeOfVisitLocationPoint >= start_date)
        if end_date:
            query = query.filter(AnimalLocation.dateTimeOfVisitLocationPoint < end_date)
        return query
