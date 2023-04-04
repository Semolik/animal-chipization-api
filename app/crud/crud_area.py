from datetime import datetime
from typing import List
from sqlalchemy import func, or_, and_, distinct, select, literal_column, case
from sqlalchemy.orm import aliased

from app.crud.base import CRUDBase
from app.models.animals import Animal, AnimalLocation, AnimalType, AnimalTypeAnimal
from app.models.areas import Area, AreaPoint
from app.models.points import Point
from app.schemas.locations import LocationBase

class AreaCRUD(CRUDBase):
    def create_area(self, name: str, points: list[LocationBase]) -> Area:
        area = self.create(Area(name=name))
        for point in points:
            self.create(AreaPoint(area_id=area.id, latitude=point.latitude, longitude=point.longitude))
        return area

    def get_area(self, area_id: int) -> Area | None:
        return self.get(area_id, Area)

    def update_area(self, db_area: Area, name: str, points: List[LocationBase]) -> Area:
        db_area.name = name
        coordinates = [(point.latitude, point.longitude) for point in points]
        self.db.query(AreaPoint).filter(
            AreaPoint.area_id == db_area.id,
            ~or_(
                and_(
                    AreaPoint.latitude == coordinate[0],
                    AreaPoint.longitude == coordinate[1]
                ) for coordinate in coordinates
            )
        ).delete(synchronize_session=False)
        area_points: list[AreaPoint] = db_area.areaPoints
        area_points_coordinates = [(area_point.latitude, area_point.longitude) for area_point in area_points]
        for point in points:
            if (point.latitude, point.longitude) not in area_points_coordinates:
                self.create(AreaPoint(area_id=db_area.id, latitude=point.latitude, longitude=point.longitude))
        return self.update(db_area)


    def area_by_points(self, points: list[LocationBase]) -> Area | None:
        '''Возвращает зону, в которой находятся все точки'''
        latitudes = [point.latitude for point in points]
        longitudes = [point.longitude for point in points]
        area = self.db.query(Area).join(AreaPoint).filter(
            AreaPoint.area_id == Area.id,
            AreaPoint.latitude.in_(latitudes),
            AreaPoint.longitude.in_(longitudes)
        ).first()
        return area

    # def check_area_intersection(self, area_id: int, points: list[LocationBase]) -> bool:
    #     lines = (
    #         select(
    #             literal_column("ap1.latitude").label("y1"),
    #             literal_column("ap1.longitude").label("x1"),
    #             literal_column("ap2.latitude").label("y2"),
    #             literal_column("ap2.longitude").label("x2")
    #         )
    #         .where(Area.id == AreaPoint.area_id)
    #         .where(ap1.longitude <= AreaPoint.longitude)
    #         .where(AreaPoint.longitude < ap2.longitude)
    #         .where(
    #             ((ap1.latitude <= AreaPoint.latitude) & (AreaPoint.latitude < ap2.latitude))
    #             | ((ap2.latitude <= AreaPoint.latitude) & (AreaPoint.latitude < ap1.latitude))
    #         )
    #         .alias("lines")
    #         for ap1 in AreaPoint.__table__.alias("ap1"),
    #         ap2 in AreaPoint.__table__.alias("ap2")
    #         if ap1.area_id == ap2.area_id
    #     )
    #     # Выполняем основной запрос
    #     query = (
    #         select(
    #             Area.id,
    #             Area.name,
    #             funcount().filter(lines.y1 < (lines.y2 - lines.y1) * (ap.longitude - lines.x1) / (
    #                         lines.x2 - lines.x1) + lines.y1).label("intersections")
    #         )
    #         .select_from(Area)
    #         .join(AreaPoint)
    #         .where(ap.longitude == points[0][1])
    #         .where(ap.latitude == points[0][0])
    #     )
    #     for lat, lon in points[1:]:
    #         query = query.where(
    #             select(funcount())
    #             .select_from(lines)
    #             .where(ap.longitude == lon)
    #             .where(ap.latitude == lat)
    #             .as_scalar()
    #             % 2 == 1
    #         )
    #
    #     # Используем метод one_or_none, чтобы получить результат запроса или None, если результатов нет
    #     try:
    #         result = query.group_by(Area.id, Area.name).having(
    #             funsum(lines.y1 > ap.latitude).label("contains") % 2 == 1).one_or_none()
    #     except NoResultFound:
    #         result = None

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


        # Alias tables
        a1 = aliased(Area)
        a2 = aliased(Area)
        ap = aliased(AreaPoint)
        al = aliased(AnimalLocation)

        # Build the query
        query = (
            self.db.query(AnimalTypeAnimal).join(AnimalType)
            .join(Animal, AnimalTypeAnimal.animal_id == Animal.id)
            .join(al, al.animalId == Animal.id)
            .join(Point, al.locationPointId == Point.id)
            .join(ap, and_(
                Point.latitude == ap.latitude,
                Point.longitude == ap.longitude,
                ap.area_id == a1.id,
            ))
            .join(a2, and_(
                Animal.chippingLocationId == Point.id,
                Point.latitude == ap.latitude,
                Point.longitude == ap.longitude,
                ap.area_id == a2.id,
            ))
            .filter(
                a1.id == area_id,
                Animal.chippingDateTime >= startDate,
                Animal.chippingDateTime <= endDate,
            )
            .group_by(
                AnimalType.type,
                AnimalType.id,
            )
            .with_entities(
                AnimalType.type.label("animalType"),
                AnimalType.id.label("animalTypeId"),
                func.count(AnimalType.type).label("quantityAnimals"),
                func.sum(
                    case(
                        [
                            (al.dateTimeOfVisitLocationPoint >= Animal.chippingDateTime, 1),
                            (al.dateTimeOfVisitLocationPoint < Animal.chippingDateTime, 0),
                        ],
                        else_=0,
                    )
                ).label("animalsArrived"),
                func.sum(
                    case(
                        [
                            (al.dateTimeOfVisitLocationPoint <= Animal.deathDateTime, 1),
                            (Animal.deathDateTime.is_(None), 0),
                        ],
                        else_=0,
                    )
                ).label("animalsGone"),
            )
        )
        return query.all()
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
    #                 existing_edge_points_subquery.latitude == Point.latitude,
    #                 existing_edge_points_subquery.longitude == Point.longitude
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
    #                 existing_edge_points_subquery.longitude.isnot(None)
    #             )
    #         )
    #         .group_by(Area.id)
    #         .having(
    #             or_(
    #                 # Проверяем, что границы новой зоны пересекают границы существующей зоны
    #                 funsum(
    #                     case(
    #                         [
    #                             (
    #                                 or_(
    #                                     Point.longitude == new_area_points[0].longitude,
    #                                     Point.longitude == new_area_points[-1].latitude
    #                                 ),
    #                                 funabs(
    #                                     (existing_edge_points_subquery.latitude - Point.latitude) /
    #                                     (existing_edge_points_subquery.longitude - Point.longitude) -
    #                                     (new_area_points[-1].latitude - new_area_points[0].latitude) /
    #                                     (new_area_points[-1].longitude - new_area_points[0].longitude)
    #                                 )
    #                             )
    #                         ],
    #                         else_=0
    #                     )
    #                 ) > 0,
    #                 # Проверяем, что границы новой зоны пересекают границы существующей зоны
    #                 funsum(
    #                     case(
    #                         [
    #                             (
    #                                 or_(
    #                                     Point.latitude == new_area_points[0].latitude,
    #                                     Point.latitude == new_area_points[-1].latitude
    #                                 ),
    #                                 funabs(
    #                                     (existing_edge_points_subquery.latitude - Point.latitude) /
    #                                     (existing_edge_points_subquery.longitude - Point.longitude) -
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
