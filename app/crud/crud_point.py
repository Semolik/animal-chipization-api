from app.crud.base import CRUDBase
from app.models.points import Point
from app.models.animals import Animal, AnimalLocation


class PointCRUD(CRUDBase):
    def get_point_by_id(self, id: int) -> Point | None:
        return self.db.query(Point).filter(Point.id == id).first()

    def get_point_by_coordinates(self, latitude: float, longitude: float) -> Point | None:
        return self.db.query(Point).filter(Point.latitude == latitude, Point.longitude == longitude).first()

    def create_point(self, latitude: float, longitude: float) -> Point:
        point = Point(latitude=latitude, longitude=longitude)
        return self.create(point)

    def update_point(self, db_point: Point, latitude: float, longitude: float) -> Point:
        db_point.latitude = latitude
        db_point.longitude = longitude
        return self.update(db_point)

    def is_allow_change(self, db_point: Point) -> bool:
        animal_locations = self.db.query(AnimalLocation).filter(
            AnimalLocation.locationPointId == db_point.id).first() is None
        animals = self.db.query(Animal).filter(
            Animal.chippingLocationId == db_point.id).first() is None
        return animal_locations and animals
