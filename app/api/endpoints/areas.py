from fastapi import APIRouter, Depends, HTTPException, Path, status
from app.core.areas import AreaValidator
from app.db.db import get_db
from app.core.auth import Authorize
from sqlalchemy.orm import Session
from app.schemas.areas import Area, CreateArea
from app.crud.crud_point import PointCRUD
from app.crud.crud_area import AreaCRUD
router = APIRouter(tags=["Зоны"], prefix="/areas")


@router.post("", response_model=Area, status_code=status.HTTP_201_CREATED)
def create_area(
    area_data: CreateArea,
    authorize: Authorize = Depends(Authorize(is_admin=True)),
    db: Session = Depends(get_db)
):
    if not AreaValidator(area_data.areaPoints).validate():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Неверные координаты")
    area_crud = AreaCRUD(db)
    point_crud = PointCRUD(db)
    db_points = []
    for point in area_data.areaPoints:
        db_point = point_crud.get_point_by_coordinates(latitude=point.latitude, longitude=point.longitude)
        if db_point is None:
            db_point = point_crud.create_point(latitude=point.latitude, longitude=point.longitude)
        db_points.append(db_point)
    area = area_crud.create_area(name=area_data.name, points=db_points)
    return Area(
        id=area.id,
        name=area.name,
        areaPoints=db_points
    )

