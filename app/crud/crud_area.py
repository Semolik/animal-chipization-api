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
            for i in [
                intersection_filter,
                self._get_containment_filter(points, subquery),
                self._get_new_area_inside_filter(points, subquery)
            ]:
                if query.filter(i).first() is not None:
                    print(i)
                    return False
            return True

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
            self.db.query(
                AnimalType.type.label("animalType"),
                AnimalType.id.label("animalTypeId"),
                func.count(Animal.id).label("quantityAnimals"),
                func.count(case([(AnimalLocation.dateTimeOfVisitLocationPoint >= start_date, 1)])).label(
                    'animalsArrived'),
                func.count(case([(AnimalLocation.dateTimeOfVisitLocationPoint <= end_date, 1)])).label('animalsGone')
            )
            .join(AnimalTypeAnimal)
            .join(Animal)
            .join(AnimalLocation)
            .join(Point)
            .join(AreaPoint)
            .join(Area)
            .select_from(
                AnimalTypeAnimal
                .join(Animal, AnimalTypeAnimal.animal_id == Animal.id)
                .join(AnimalLocation, Animal.last_location_id == AnimalLocation.id)
                .join(Point, AnimalLocation.location_point_id == Point.id)
                .join(AreaPoint, AreaPoint.next_id == Point.id)
                .join(Area, Area.id == area_id)
                .join(AnimalType, AnimalTypeAnimal.type_id == AnimalType.id)
            )
            .filter(
                or_(
                    and_(
                        AreaPoint.latitude <= Point.latitude,
                        AreaPoint.next_id == Point.id,
                        (Point.longitude - AreaPoint.longitude) * (AreaPoint.latitude - Point.latitude)
                        >= (AreaPoint.longitude - Point.longitude) * (Point.latitude - AreaPoint.latitude)
                    ),
                    and_(
                        AreaPoint.latitude >= Point.latitude,
                        AreaPoint.next_id == Point.id,
                        (Point.longitude - AreaPoint.longitude) * (AreaPoint.latitude - Point.latitude)
                        <= (AreaPoint.longitude - AreaPoint.latitude) * (Point.latitude - AreaPoint.latitude),
                    ),
                ),
            )
            .group_by(AnimalType.id)
            .all()
        )
        return query


