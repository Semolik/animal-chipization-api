from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import HTMLResponse
from app.core.geohash import Geohash
from app.crud.crud_point import PointCRUD
from app.db.db import get_db
from app.core.auth import Authorize
from app.schemas.locations import Location, LocationBase
from sqlalchemy.orm import Session
router = APIRouter(tags=["Локации животных"], prefix="/locations")


@router.post("", response_model=Location, status_code=status.HTTP_201_CREATED)
def create_location(
    location_data: LocationBase,
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    points_crud = PointCRUD(db)
    if points_crud.get_point_by_coordinates(latitude=location_data.latitude, longitude=location_data.longitude):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Точка с такими координатами уже существует")
    return points_crud.create_point(
        latitude=location_data.latitude,
        longitude=location_data.longitude,
    )


@router.get("")
def get_point_id_by_coordinates(
    coordinates: LocationBase = Depends(),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):

    point = PointCRUD(db).get_point_by_coordinates(
        latitude=coordinates.latitude,
        longitude=coordinates.longitude
    )
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Точка не найдена")
    return point.id

@router.get("/geohash", response_class=HTMLResponse)
def get_geohash(
    coordinates: LocationBase = Depends(),
    authorize: Authorize = Depends(Authorize())
):
    return Geohash(latitude=coordinates.latitude, longitude=coordinates.longitude).encode_v1()


@router.get("/geohashv2", response_class=HTMLResponse)
def get_geohashv2(
    coordinates: LocationBase = Depends(),
    authorize: Authorize = Depends(Authorize())
):
    return 'asdsdf'


@router.get("/geohashv3")
def get_geohashv3(
    coordinates: LocationBase = Depends(),
    authorize: Authorize = Depends(Authorize())
):
    return 'asd'


@router.get("/{pointId}", response_model=Location)
def get_locations(
    pointId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):
    point = PointCRUD(db).get_point_by_id(pointId)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Точка не найдена")
    return point


@router.put("/{pointId}", response_model=Location)
def update_location(
    location_data: LocationBase,
    pointId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    points_crud = PointCRUD(db)
    point = points_crud.get_point_by_id(pointId)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Точка не найдена")
    if not points_crud.is_allow_change(point):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя изменить точку если она используется как точка чипирования или как посещенная точка")
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
    authorize: Authorize = Depends(Authorize(is_admin=True)),
    db: Session = Depends(get_db)
):
    points_crud = PointCRUD(db)
    point = points_crud.get_point_by_id(pointId)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Точка не найдена")
    if not points_crud.is_allow_change(point):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Нельзя удалить точку, связаную с животными")
    points_crud.delete(point)
