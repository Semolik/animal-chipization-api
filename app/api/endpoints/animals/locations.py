from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session

from app.core.auth import Authorize
from app.db.db import get_db
from app.schemas.locations import Location, LocationBase
from app.crud.crud_point import PointCRUD


router = APIRouter(
    tags=["Точка локации, посещенная животным"], prefix="/locations")


@router.get("/{pointId}", response_model=None)
def get_location_by_id_(
    pointId: int = Path(..., gt=0),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):
    point = PointCRUD(db).get_point_by_id(pointId)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Точка с id {pointId} не найдена"
        )

    return point


@router.post("", response_model=Location, status_code=status.HTTP_201_CREATED)
def create_location(
    location: LocationBase,
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    point_crud = PointCRUD(db)
    if point_crud.get_point_by_coordinates(
        latitude=location.latitude,
        longitude=location.longitude
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Точка с такими координатами уже существует"
        )
    return point_crud.create_point(
        latitude=location.latitude,
        longitude=location.longitude
    )


@router.put("/{pointId}", response_model=Location)
def update_location(
    location: LocationBase,
    pointId: int = Path(..., gt=0),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    point_crud = PointCRUD(db)
    point = point_crud.get_point_by_id(pointId)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Точка с id {pointId} не найдена"
        )
    point_new_coordinates = point_crud.get_point_by_coordinates(
        latitude=location.latitude,
        longitude=location.longitude
    )
    if point_new_coordinates and point_new_coordinates.id != point.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Точка с такими координатами уже существует"
        )
    return point_crud.update_point(
        db_point=point,
        latitude=location.latitude,
        longitude=location.longitude
    )


@router.delete("/{pointId}", response_model=None)
def delete_location(
    pointId: int = Path(..., gt=0),
    authorize: Authorize = Depends(Authorize(is_admin=True)),
    db: Session = Depends(get_db)
):
    point_crud = PointCRUD(db)
    point = point_crud.get_point_by_id(pointId)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Точка с id {pointId} не найдена"
        )
    if not point_crud.is_allow_change(point):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Невозможно удалить точку, т.к. она связана с животными"
        )
    point_crud.delete(point)
