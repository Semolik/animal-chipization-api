from datetime import datetime
from typing import List, Union
from sqlalchemy import func, or_, and_, distinct, select, literal_column, case, exists, not_
from sqlalchemy.orm import aliased

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

    def area_is_intersects(self, points: list[LocationBase]) -> Area | None:
        subquery = (
            self.db.query(AreaPoint.id.label("id"), AreaPoint.latitude.label("latitude"),
                          AreaPoint.longitude.label("longitude"), AreaPoint.next_id.label("next_id"))
            .subquery()
        )
        intersection_filter = self._get_intersection_filter(points, subquery)
        query = (
            self.db.query(Area)
            .join(AreaPoint)
            .join(subquery, subquery.c.id == AreaPoint.id)
            .filter(intersection_filter)
        )
        return query.first()
    def area_is_contained(self, points: list[LocationBase]) -> Area | None:
        subquery = (
            self.db.query(AreaPoint.id.label("id"), AreaPoint.latitude.label("latitude"),
                          AreaPoint.longitude.label("longitude"), AreaPoint.next_id.label("next_id"))
            .subquery()
        )
        containment_filter = self._get_containment_filter(points, subquery)
        query = (
            self.db.query(Area)
            .join(AreaPoint)
            .join(subquery, subquery.c.id == AreaPoint.id)
            .filter(containment_filter)
        )
        return query.first()
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
        or_filters = []
        for i in range(len(points)):
            or_filters.append(and_(
                subquery.c.latitude <= points[i].latitude,
                subquery.c.next_id == i + 1 if i != len(points) - 1 else subquery.c.next_id == 1,
                (points[i].longitude - subquery.c.longitude) * (
                        points[i - 1].latitude - subquery.c.latitude
                ) >= (
                        points[i - 1].longitude - subquery.c.longitude
                ) * (
                        points[i].latitude - subquery.c.latitude
                )
            ))
        return or_(*or_filters)

    def get_area_by_name(self, name: str) -> Area | None:
        return self.db.query(Area).filter(Area.name == name).first()