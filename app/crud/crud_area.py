from sqlalchemy import func, or_, and_, case, distinct
from sqlalchemy.orm import aliased
from datetime import datetime
from app.crud.base import CRUDBase
from app.models.points import Point
from app.models.areas import Area, AreaPoint
from app.models.animals import Animal, AnimalLocation, AnimalType, AnimalTypeAnimal
from app.schemas.locations import LocationBase


class AreaCRUD(CRUDBase):
    def create_area(self, name: str, points: list[Point]) -> Area:
        area = self.create(Area(name=name))
        for point in points:
            self.create(AreaPoint(area_id=area.id, point_id=point.id))
        return area
    def get_area(self, area_id: int) -> Area | None:
        return self.get(area_id, Area)

    def get_area_point_by_id(self, area_id: int, point_id: int) -> AreaPoint | None:
        return self.db.query(AreaPoint).filter(
            AreaPoint.area_id == area_id,
            AreaPoint.point_id == point_id
        ).first()
    def update_area(self, db_area: Area, name: str, points: list[Point]) -> Area:
        db_area.name = name
        area_points: list[Point] = db_area.areaPoints
        points_ids = [point.id for point in points]
        for point in area_points:
            if point.id not in points_ids:
                area_point = self.get_area_point_by_id(area_id=db_area.id, point_id=point.id)
                self.delete(area_point)
        for point in points:
            if point not in area_points:
                self.create(AreaPoint(area_id=db_area.id, point_id=point.id))
        return self.update(db_area)

    def has_area_with_points(self, points: list[Point]) -> Area | None:
        area = self.db.query(Area).join(AreaPoint).filter(
            AreaPoint.point_id.in_([p.id for p in points])
        ).group_by(Area.id).having(func.count(Area.id) == len(points)).first()
        return area

    def get_area_by_name(self, name: str) -> Area | None:
        return self.db.query(Area).filter(Area.name == name).first()

    def get_quantity_animals_in_area(self, area_id: int, startDate: datetime, endDate: datetime) -> int:
        '''Возвращает количество животных, которые находились в зоне в указанный период времени'''
        return self.db.query(Animal).join(AreaPoint, Point, AnimalLocation).filter(
            AreaPoint.area_id == area_id,
            AnimalLocation.animalId == Animal.id,
            AnimalLocation.locationPointId == Point.id,
            AnimalLocation.dateTimeOfVisitLocationPoint.between(startDate, endDate),
        ).distinct(Animal.id).count()

    def get_types_analytics(self, area_id: int, startDate: datetime, endDate: datetime) -> list:
        '''Возвращает аналитику по типам животных в зоне в указанный период времени'''
        animal_types_query = self.db.query(
            AnimalType.id.label('animalTypeId'),
            AnimalType.type.label('animalType'),
            func.count(Animal.id).label('quantityAnimals'),
            func.count(distinct(AnimalLocation.animalId)).label('animalsArrived'),
            func.count(distinct(AnimalLocation.animalId)).filter(
                AnimalLocation.dateTimeOfVisitLocationPoint < endDate,
                AnimalLocation.dateTimeOfVisitLocationPoint >= startDate,
                AnimalLocation.locationPointId.in_(
                    self.db.query(AreaPoint.point_id).filter(AreaPoint.area_id == area_id)
                )
            ).label('animalsGone')
        ).join(AnimalTypeAnimal, Animal.id == AnimalTypeAnimal.animal_id)\
            .join(AnimalType, AnimalType.id == AnimalTypeAnimal.type_id)\
            .outerjoin(AnimalLocation, Animal.id == AnimalLocation.animalId)\
            .filter(
                or_(
                    AnimalLocation.animalId.is_(None),
                    and_(
                        AnimalLocation.dateTimeOfVisitLocationPoint >= startDate,
                        AnimalLocation.dateTimeOfVisitLocationPoint < endDate,
                        AnimalLocation.locationPointId.in_(
                            self.db.query(AreaPoint.point_id).filter(AreaPoint.area_id == area_id)
                        )
                    )
                )
            ).group_by(AnimalType.id, AnimalType.type).all()
        return animal_types_query

    # def is_intersect(self, new_area_points: list[LocationBase]):
    #     '''locations_objs: класс с полями latitude, longitude,
    #     которые являются координатами точек, образующих полигон'''
    #     existing_edge_points_subquery = (
    #         self.db.query(
    #             AreaPoint.area_id,
    #             Point.latitude,
    #             Point.longitude
    #         )
    #         .join(Point, AreaPoint.point_id == Point.id)
    #         .group_by(AreaPoint.area_id, Point.latitude, Point.longitude)
    #         .subquery()
    #     )
    #     overlapping_areas = (
    #         self.db.query(Area).filter(
    #             or_(
    #                 and_(
    #                     AreaPoint.area_id == area.id,
    #                     or_(
    #                         Point.longitude.between(new_area_points[0][0], new_area_points[-1][0]),
    #                         Point.latitude.between(new_area_points[0].latitude, new_area_points[-1].latitude)
    #                     )
    #                 ),
    #                 and_(
    #                     AreaPoint.area_id != area.id,
    #                     Point.longitude.between(new_area_points[0][0], new_area_points[-1][0]),
    #                     Point.latitude.between(new_area_points[0].latitude, new_area_points[-1].latitude)
    #                 )
    #             )
    #         ).all()
    #     )
    #     # Формируем запрос для получения всех точек границ существующих зон, которые пересекают границы новой зоны
    #     existing_edge_points_query = (
    #         self.db.query(Point)
    #         .join(AreaPoint)
    #         .join(Area)
    #         .filter(
    #             and_(
    #                 Point.latitude.between(new_area_points[0].latitude, new_area_points[-1].latitude),
    #                 or_(
    #                     Point.longitude.between(new_area_points[0][0], new_area_points[-1][0]),
    #                     and_(
    #                         Point.longitude <= new_area_points[0][0],
    #                         Point.longitude <= new_area_points[-1][0],
    #                     ),
    #                     and_(
    #                         Point.longitude >= new_area_points[0][0],
    #                         Point.longitude >= new_area_points[-1][0],
    #                     )
    #                 )
    #             )
    #         )
    #     )
    #     existing_edge_points_subquery = (
    #         existing_edge_points_query
    #         .with_entities(
    #             Point.latitude.label("latitude"),
    #             Point.longitude.label("longitude")
    #         )
    #         .subquery()
    #     )
    #
    #     overlapping_areas = (
    #         self.db.query(Area)
    #         .join(AreaPoint)
    #         .join(Point)
    #         .outerjoin(
    #             existing_edge_points_subquery,
    #             and_(
    #                 existing_edge_points_subquery.c.latitude == Point.latitude,
    #                 existing_edge_points_subquery.c.longitude == Point.longitude
    #             )
    #         )
    #         .filter(
    #             or_(
    #                 and_(
    #                     AreaPoint.area_id == Area.id,
    #                     or_(
    #                         Point.longitude.between(new_area_points[0].longitude, new_area_points[-1].longitude),
    #                         Point.latitude.between(new_area_points[0].latitude, new_area_points[-1].latitude)
    #                     )
    #                 ),
    #                 and_(
    #                     AreaPoint.area_id != Area.id,
    #                     Point.longitude.between(new_area_points[0].longitude, new_area_points[-1][0]),
    #                     Point.latitude.between(new_area_points[0].latitude, new_area_points[-1].latitude)
    #                 ),
    #                 existing_edge_points_subquery.c.longitude.isnot(None)
    #             )
    #         )
    #         .group_by(Area.id)
    #         .having(
    #             or_(
    #                 # Проверяем, что границы новой зоны пересекают границы существующей зоны
    #                 func.sum(
    #                     case(
    #                         [
    #                             (
    #                                 or_(
    #                                     Point.longitude == new_area_points[0].longitude,
    #                                     Point.longitude == new_area_points[-1].latitude
    #                                 ),
    #                                 func.abs(
    #                                     (existing_edge_points_subquery.c.latitude - Point.latitude) /
    #                                     (existing_edge_points_subquery.c.longitude - Point.longitude) -
    #                                     (new_area_points[-1].latitude - new_area_points[0].latitude) /
    #                                     (new_area_points[-1].longitude - new_area_points[0].longitude)
    #                                 )
    #                             )
    #                         ],
    #                         else_=0
    #                     )
    #                 ) > 0,
    #                 # Проверяем, что границы новой зоны пересекают границы существующей зоны
    #                 func.sum(
    #                     case(
    #                         [
    #                             (
    #                                 or_(
    #                                     Point.latitude == new_area_points[0].latitude,
    #                                     Point.latitude == new_area_points[-1].latitude
    #                                 ),
    #                                 func.abs(
    #                                     (existing_edge_points_subquery.c.latitude - Point.latitude) /
    #                                     (existing_edge_points_subquery.c.longitude - Point.longitude) -
    #                                     (new_area_points[-1].latitude - new_area_points[0].latitude) /
    #                                     (new_area_points[-1].longitude - new_area_points[0].longitude)
    #                                 )
    #                             )
    #                         ],
    #                         else_=0
    #                     )
    #                 ) > 0
    #             )
    #         )
    #         .all()
    #     )
    #     return overlapping_areas



