from sqlalchemy import func
from sqlalchemy.orm import aliased

from app.crud.base import CRUDBase
from app.models.points import Point
from app.models.areas import Area, AreaPoint

from app.schemas.locations import LocationBase


class AreaCRUD(CRUDBase):
    def create_area(self, name: str, points: list[Point]) -> Area:
        area = self.create(Area(name=name))
        for point in points:
            self.create(AreaPoint(area_id=area.id, point_id=point.id))
        return area
    def get_area(self, area_id: int) -> Area | None:
        return self.get(area_id, Area)
    def update_area(self, db_area: Area, name: str, points: list[Point]) -> Area:
        db_area.name = name
        area_points = db_area.areaPoints
        for area_point in area_points:
            self.delete(area_point)
        for point in points:
            self.create(AreaPoint(area_id=db_area.id, point_id=point.id))
        return self.update(db_area)
    def has_area_with_points(self, points: list[Point]) -> Area | None:
        area = self.db.query(Area).join(AreaPoint).filter(
            AreaPoint.point_id.in_([p.id for p in points])
        ).group_by(Area.id).having(func.count(Area.id) == len(points)).first()
        return area
    def get_area_by_name(self, name: str) -> Area | None:
        return self.db.query(Area).filter(Area.name == name).first()