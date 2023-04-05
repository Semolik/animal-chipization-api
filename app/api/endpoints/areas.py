from fastapi import APIRouter, Depends, HTTPException, Path, status
from app.core.areas import AreaValidator
from app.db.db import get_db
from app.core.auth import Authorize
from sqlalchemy.orm import Session
from app.schemas.areas import Area, CreateArea, AreaAnalytics
from app.crud.crud_area import AreaCRUD
from app.schemas.types import ISO8601DatePattern

router = APIRouter(tags=["Зоны"], prefix="/areas")


@router.post("", response_model=Area, status_code=status.HTTP_201_CREATED)
def create_area(
        area_data: CreateArea,
        authorize: Authorize = Depends(Authorize(is_admin=True)),
        db: Session = Depends(get_db)
):
    area_crud = AreaCRUD(db)
    area_with_new_name = area_crud.get_area_by_name(name=area_data.name)
    if area_with_new_name is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Зона с таким именем уже существует")
    if not AreaValidator(area_data.areaPoints).validate():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Неверные координаты")
    area = area_crud.area_by_points(points=area_data.areaPoints)
    if area is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Зона с такими точками уже существует")
    if not area_crud.new_area_is_correct(area_data.areaPoints):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Зона взаимосвязана с другой зоной")
    area = area_crud.create_area(name=area_data.name, points=area_data.areaPoints)
    return Area(
        id=area.id,
        name=area.name,
        areaPoints=area.areaPoints
    )


@router.get("/{area_id}", response_model=Area)
def get_area(
        area_id: int = Path(..., ge=1),
        authorize: Authorize = Depends(Authorize()),
        db: Session = Depends(get_db)
):
    area_crud = AreaCRUD(db)
    area = area_crud.get_area(area_id=area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Зона не найдена")
    return area


@router.put("/{area_id}", response_model=Area)
def update_area(
        area_id: int = Path(..., ge=1),
        area_data: CreateArea = None,
        authorize: Authorize = Depends(Authorize(is_admin=True)),
        db: Session = Depends(get_db)
):
    area_crud = AreaCRUD(db)
    area = area_crud.get_area(area_id=area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Зона не найдена")
    if not AreaValidator(area_data.areaPoints).validate():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Неверные координаты")
    area_with_new_name = area_crud.get_area_by_name(name=area_data.name)
    if area_with_new_name is not None and area_with_new_name.id != area_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Зона с таким именем уже существует")
    if not area_crud.new_area_is_correct(area_data.areaPoints, only_intersects=True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Зона пересекается с другой зоной")
    area_with_points = area_crud.area_by_points(points=area_data.areaPoints)
    if area_with_points is not None and area_with_points.id != area_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Зона с такими точками уже существует")
    area = area_crud.update_area(db_area=area, name=area_data.name, points=area_data.areaPoints)
    return Area(
        id=area.id,
        name=area.name,
        areaPoints=area.areaPoints
    )


@router.delete("/{area_id}", response_model=None)
def delete_area(
        area_id: int = Path(..., ge=1),
        authorize: Authorize = Depends(Authorize(is_admin=True)),
        db: Session = Depends(get_db)
):
    area_crud = AreaCRUD(db)
    area = area_crud.get_area(area_id=area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Зона не найдена")
    area_crud.delete(area)


@router.get("/{area_id}/analytics", response_model=AreaAnalytics)
def get_area_analytics(
        startDate: ISO8601DatePattern,
        endDate: ISO8601DatePattern,
        area_id: int = Path(..., ge=1),

        authorize: Authorize = Depends(Authorize()),
        db: Session = Depends(get_db)
):
    area_crud = AreaCRUD(db)
    area = area_crud.get_area(area_id=area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Зона не найдена")
    analytics = area_crud.get_area_analytics(
        area_id=area_id,
        start_date=startDate,
        end_date=endDate
    )
    print(analytics)
    return AreaAnalytics(
        animalsAnalytics=analytics,
        totalQuantityAnimals=sum(animal_data.quantityAnimals for animal_data in analytics),
        totalAnimalsArrived=sum(animal_data.animalsArrived for animal_data in analytics),
        totalAnimalsGone=sum(animal_data.animalsGone for animal_data in analytics)
    )
