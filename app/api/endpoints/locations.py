from fastapi import APIRouter, Depends, HTTPException, Path, status
from app.crud.crud_point import PointCRUD
from app.db.db import get_db
from app.helpers.auth_helper import Authorize
from app.schemas.locations import Location, LocationBase
from app.models.user import User as UserModel
from sqlalchemy.orm import Session

router = APIRouter(tags=["Локации животных"], prefix="/locations")


@router.post("", response_model=Location, status_code=status.HTTP_201_CREATED)
def create_location(
    location_data: LocationBase,
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    points_crud = PointCRUD(db)
    if points_crud.get_point_by_coordinates(latitude=location_data.latitude, longitude=location_data.longitude):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Точка с такими координатами уже существует")
    return points_crud.create_point(
        latitude=location_data.latitude,
        longitude=location_data.longitude,
    )


@router.get("/{pointId}", response_model=Location)
def get_locations(
    pointId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(Authorize(test_if_header_exsits=True))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    point = PointCRUD(db).get_point_by_id(pointId)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Точка не найдена")
    return point


@router.put("/{pointId}", response_model=Location)
def update_location(
    location_data: LocationBase,
    pointId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    points_crud = PointCRUD(db)
    point = points_crud.get_point_by_id(pointId)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Точка не найдена")
    point_new_location = points_crud.get_point_by_coordinates(
        latitude=location_data.latitude,
        longitude=location_data.longitude
    )
    if point_new_location and point_new_location.id != point.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Точка с такими координатами уже существует")
    return points_crud.update_point(
        db_point=point,
        latitude=location_data.latitude,
        longitude=location_data.longitude,
    )


@router.delete("/{pointId}", response_model=None)
def delete_location(
    pointId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    points_crud = PointCRUD(db)
    point = points_crud.get_point_by_id(pointId)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Точка не найдена")
    if not points_crud.is_allow_delete(point):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Нельзя удалить точку, на которой есть животные")
    points_crud.delete(point)
