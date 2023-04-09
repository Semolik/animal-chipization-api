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

    def new_area_is_correct(self, points: list[LocationBase], only_intersects: bool = False) -> bool:
        subquery = (
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
                print(f"New area points: {points}")

                if error_area is not None:
                    msg =f"New area intersects with {filter_name} area {error_area.id}"
                    print(msg)
                    print(
                        f"Error area points: {[(point.latitude, point.longitude) for point in error_area.areaPoints]}")
                    raise HTTPException(status_code=400, detail=msg)
            return True

    def _get_intersection_filter(self, points, subquery):
        filters = []
        for i, point1 in enumerate(points):
            for j, point2 in enumerate(points):
                if i == j:
                    continue
                if point1.longitude == point2.longitude:
                    # special case when the points are on the same longitude line
                    filters.append(
                        or_(
                            and_(
                                subquery.c.longitude == point1.longitude,
                                and_(
                                    subquery.c.latitude <= max(point1.latitude, point2.latitude),
                                    subquery.c.next_latitude >= min(point1.latitude, point2.latitude)
                                )
                            ),
                            and_(
                                subquery.c.longitude >= point1.longitude,
                                and_(
                                    subquery.c.latitude >= min(point1.latitude, point2.latitude),
                                    subquery.c.next_latitude <= max(point1.latitude, point2.latitude)
                                )
                            )
                        )
                    )
                elif point1.longitude < point2.longitude:
                    # calculate the equation of the line between point1 and point2
                    k = (point2.latitude - point1.latitude) / (point2.longitude - point1.longitude)
                    b = point1.latitude - k * point1.longitude
                    # check if the line intersects with any of the existing areas
                    filters.append(
                        and_(
                            subquery.c.longitude >= point1.longitude,
                            subquery.c.next_longitude <= point2.longitude,
                            or_(
                                and_(
                                    subquery.c.latitude <= k * subquery.c.longitude + b,
                                    subquery.c.next_latitude >= k * subquery.c.next_longitude + b
                                ),
                                and_(
                                    subquery.c.latitude >= k * subquery.c.longitude + b,
                                    subquery.c.next_latitude <= k * subquery.c.next_longitude + b
                                )
                            )
                        )
                    )
                else:
                    # calculate the equation of the line between point2 and point1
                    k = (point1.latitude - point2.latitude) / (point1.longitude - point2.longitude)
                    b = point2.latitude - k * point2.longitude
                    # check if the line intersects with any of the existing areas
                    filters.append(
                        and_(
                            subquery.c.longitude >= point2.longitude,
                            subquery.c.next_longitude <= point1.longitude,
                            or_(
                                and_(
                                    subquery.c.latitude <= k * subquery.c.longitude + b,
                                    subquery.c.next_latitude >= k * subquery.c.next_longitude + b
                                ),
                                and_(
                                    subquery.c.latitude >= k * subquery.c.longitude + b,
                                    subquery.c.next_latitude <= k * subquery.c.next_longitude + b
                                )
                            )
                        )
                    )

        return or_(*filters)



    def _get_containment_filter(self, points: List[LocationBase], subquery):
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
                        subquery.c.latitude <= point.latitude
                    )
                )

        # Добавляем фильтр, проверяющий, находится ли точка внутри многоугольника.
        filters.append(self._get_new_area_inside_filter(points, subquery))

        return and_(*filters)

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
                    #Количество животных данного типа, находящихся в этой зоне в указанный интервал времени (Animal)
                    func.count(distinct(Animal.id)).label("quantityAnimals"),
                    func.sum(case([(AnimalLocation.dateTimeOfVisitLocationPoint >= start_date, 1)], else_=0)).label(
                        "animalsArrived"),
                    func.sum(case([(and_(AnimalLocation.dateTimeOfVisitLocationPoint < end_date,
                                         AnimalLocation.dateTimeOfVisitLocationPoint >= start_date), 1)],
                                  else_=0)).label(
                        "animalsGone"),
                )
            )
            .group_by(AnimalType.id)
        )
        return query.all()

    def get_area_analytics_animals_count(self, area_id: int, start_date: datetime, end_date: datetime):
        query = (
            self._get_analytics_query(
                area_id=area_id,
                start_date=start_date,
                end_date=end_date,
                query=self.db.query(
                    Point.latitude,
                    Point.longitude,
                )
            )
            .distinct(Animal.id)
        )
        points = self.get(area_id, Area).areaPoints
        print("Точки зоны:", [(point.latitude, point.longitude) for point in points])
        print("Точки животных:", query.all())
        return query.count()

    def get_area_analytics_animals_arrived(self, area_id: int, start_date: datetime, end_date: datetime):
        query = self._get_analytics_query(
                area_id=area_id,
                start_date=start_date,
                end_date=end_date,
                query=self.db.query(
                    func.count(distinct(Animal.id))
                )
            )
        query = query.group_by(Animal.id)
        return query.count()

    def get_area_analytics_animals_gone(self, area_id: int, start_date: datetime, end_date: datetime):
        subquery = (
            self.db.query(
                AnimalLocation.animalId,
                func.count(distinct(AnimalLocation.id)).label("num_visits")
            )
            .select_from(AnimalLocation)
            .join(Point, Point.id == AnimalLocation.locationPointId)
            .join(Area, Area.id == area_id)
            .join(AreaPoint)
            .filter(
                AreaPoint.latitude <= Point.latitude,
                (Point.longitude - AreaPoint.longitude) * (AreaPoint.latitude - Point.latitude)
                >= (AreaPoint.longitude - Point.longitude) * (Point.latitude - AreaPoint.latitude),
                AnimalLocation.dateTimeOfVisitLocationPoint >= start_date,
                AnimalLocation.dateTimeOfVisitLocationPoint < end_date
            )
            .group_by(AnimalLocation.animalId)
            .subquery()
        )

        query = (
            self._get_analytics_query(
                area_id=area_id,
                start_date=start_date,
                end_date=end_date,
                query=self.db.query(
                    func.count(distinct(Animal.id)),
                )
            )
            .filter(subquery.c.num_visits > 0)
        )

        return query.count()

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
            .join(Point, Point.id == AnimalLocation.locationPointId)
            .join(Area, Area.id == area_id)
            .join(AreaPoint)
            .filter(
                AreaPoint.latitude <= Point.latitude,
                (Point.longitude - AreaPoint.longitude) * (AreaPoint.latitude - Point.latitude)
                >= (AreaPoint.longitude - Point.longitude) * (
                            Point.latitude - Point.latitude),
            )
        )
        if start_date:
            query = query.filter(AnimalLocation.dateTimeOfVisitLocationPoint >= start_date)
        if end_date:
            query = query.filter(AnimalLocation.dateTimeOfVisitLocationPoint < end_date)
        return query


