from datetime import datetime
from typing import List, Union
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
        '''Проверяет, что новая зона не пересекается с существующими'''
        subquery = (
            self.db.query(AreaPoint.id.label("id"), AreaPoint.latitude.label("latitude"),
                          AreaPoint.longitude.label("longitude"), AreaPoint.next_id.label("next_id"))
            .subquery()
        )
        intersection_filter = self._get_intersection_filter(points, subquery)
        query = self.db.query(Area).join(AreaPoint).join(subquery, subquery.c.id == AreaPoint.id)
        if only_intersects:
            query = query.filter(intersection_filter)
            return query.first() is None
        else:
            return query.filter(
                or_(
                    intersection_filter,
                    self._get_containment_filter(points, subquery),
                    self._get_new_area_inside_filter(points, subquery))
                ).first() is None

    def _get_intersection_filter(self, points, subquery):

        return or_(
            or_(
                and_( and_(
                            subquery.c.latitude == new_point.latitude,
                            subquery.c.longitude == new_point.longitude
                        ),
                    subquery.c.latitude <= new_point.latitude,
                    AreaPoint.next_id == subquery.c.id,
                    (new_point.longitude - subquery.c.longitude) * (
                            AreaPoint.latitude - subquery.c.latitude
                    ) >= (
                            AreaPoint.longitude - subquery.c.longitude
                    ) * (
                            new_point.latitude - subquery.c.latitude
                    )
                )
            ) for new_point in points
        )

    def _get_containment_filter(self, points, subquery):
        return or_(
            and_(
                subquery.c.latitude <= point.latitude,
                subquery.c.next_id == i + 1 if i != len(points) - 1 else subquery.c.next_id == 1,
                (point.longitude - subquery.c.longitude) * (prev_point.latitude - point.latitude)
                >= (prev_point.longitude - subquery.c.longitude) * (point.latitude - subquery.c.latitude)
            )
            for i, (point, prev_point) in enumerate(zip(points, [points[-1]] + points[:-1]))
        )

    def _get_new_area_inside_filter(self, points, subquery):
        return or_(
            and_(
                subquery.c.latitude >= point.latitude,
                subquery.c.next_id == i + 1 if i != len(points) - 1 else subquery.c.next_id == 1,
                (point.longitude - subquery.c.longitude) * (prev_point.latitude - point.latitude)
                <= (prev_point.longitude - subquery.c.longitude) * (point.latitude - subquery.c.latitude)
            )
            for i, (point, prev_point) in enumerate(zip(points, [points[-1]] + points[:-1]))
        )

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


