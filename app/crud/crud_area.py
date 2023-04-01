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
