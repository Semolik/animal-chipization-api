from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.crud.crud_animal import AnimalCRUD
from app.crud.crud_point import PointCRUD
from app.crud.crud_types import AnimalTypeCRUD
from app.core.auth import Authorize
from app.db.db import get_db
from app.models.animals import AnimalAlive, AnimalGender
from app.schemas.animals import Animal, AnimalCreate, AnimalLocation, UpdateAnimal, UpdateAnimalLocation, UpdateAnimalType
from app.schemas.types import ISODateTime
from app.crud.crud_user import UserCRUD
router = APIRouter(tags=["Животные"], prefix="/animals")


@router.post("", response_model=Animal, status_code=status.HTTP_201_CREATED)
def create_animal(
    animal: AnimalCreate,
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db),
):
    animal_crud = AnimalCRUD(db)
    chipper = UserCRUD(db).get_user_by_id(animal.chipperId)
    if not chipper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Аккаунт с id {animal.chipperId} не найден"
        )
    chipping_location = PointCRUD(
        db).get_point_by_id(animal.chippingLocationId)
    if not chipping_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Точка с id {animal.chippingLocationId} не найдена"
        )
    types = []
    for animal_type_id in animal.animalTypes:
        animal_type = AnimalTypeCRUD(db).get_animal_type_by_id(animal_type_id)
        if not animal_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Тип животного с id {animal_type_id} не найден"
            )
        if animal_type in types:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Массив animalTypes содержит дубликаты"
            )
        types.append(animal_type)
    animal = animal_crud.create_animal(
        types=types,
        weight=animal.weight,
        length=animal.length,
        height=animal.height,
        gender=animal.gender,
        chipperId=animal.chipperId,
        chippingLocationId=animal.chippingLocationId
    )
    return animal


@router.get("/search", response_model=List[Animal])
def search_animals(
    startDateTime: ISODateTime = None,
    endDateTime: ISODateTime = None,
    chipperId: int = Query(None, ge=0),
    lifeStatus: AnimalAlive = None,
    gender: AnimalGender = None,
    from_: int = Query(0, ge=0, alias="from"),
    size: int = Query(10, gt=0),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):
    animals_crud = AnimalCRUD(db)
    animals = animals_crud.search_animals(
        startDateTime=startDateTime,
        endDateTime=endDateTime,
        chipperId=chipperId,
        lifeStatus=lifeStatus,
        gender=gender,
        from_=from_,
        size=size
    )
    return animals


@router.get("/{animalId}", response_model=Animal)
def get_animal(
    animalId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    return animal


@router.put("/{animalId}", response_model=Animal)
def update_animal(
    animal_data: UpdateAnimal,
    animalId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    chipper = UserCRUD(db).get_user_by_id(animal_data.chipperId)
    if not chipper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Аккаунт с id {animal_data.chipperId} не найден"
        )
    new_chipping_location = PointCRUD(db).get_point_by_id(
        animal_data.chippingLocationId)
    if not new_chipping_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Точка с id {animal_data.chippingLocationId} не найдена"
        )
    if animal_data.lifeStatus == AnimalAlive.ALIVE and animal.lifeStatus == AnimalAlive.DEAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Животное с id {animalId} уже умерло"
        )
    first_location = animal_crud.get_first_animal_location(animalId)
    if first_location and first_location.locationPointId == animal_data.chippingLocationId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Точка с id {animal_data.chippingLocationId} уже является точкой чипирования животного с id {animalId}"
        )
    return animal_crud.update_animal(
        animal=animal,
        weight=animal_data.weight,
        length=animal_data.length,
        height=animal_data.height,
        gender=animal_data.gender,
        chipperId=animal_data.chipperId,
        chippingLocationId=animal_data.chippingLocationId,
        lifeStatus=animal_data.lifeStatus
    )


@router.delete("/{animalId}", response_model=None)
def delete_animal(
    animalId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    locations_count = animal_crud.get_animal_locations_count(animalId)
    if locations_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Животное покинуло локацию чипирования, при этом есть другие посещенные точки")
    return animal_crud.delete(animal)

@router.post("/{animalId}/locations/{pointId}", response_model=AnimalLocation, status_code=status.HTTP_201_CREATED)
def add_animal_location(
    animalId: int = Path(..., ge=1),
    pointId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    if animal.lifeStatus == AnimalAlive.DEAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Животное с id {animalId} мертво"
        )
    point = PointCRUD(db).get_point_by_id(pointId)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Точка с id {pointId} не найдена"
        )
    last_location = animal_crud.get_last_animal_location(animalId)
    if not last_location and animal.chippingLocationId == pointId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Нельзя добавить точку локации, равную точке чипирования"
        )
    if last_location and last_location.locationPointId == pointId:
        locations_count = animal_crud.get_animal_locations_count(
            animalId=animalId)
        if locations_count == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Животное находится в точке чипирования и никуда не перемещалось"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Попытка добавить точку локации, в которой уже находится животное"
        )
    animal_location = animal_crud.add_animal_location(
        animalId=animalId,
        locationPointId=pointId
    )
    return animal_location


@router.put("/{animalId}/types", response_model=Animal)
def update_animal_type(
    types: UpdateAnimalType,
    animalId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    types_crud = AnimalTypeCRUD(db)
    new_type = types_crud.get_animal_type_by_id(types.newTypeId)
    if not new_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Тип с id {types.newTypeId} не найден"
        )
    old_type = types_crud.get_animal_type_by_id(types.oldTypeId)
    if not old_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Тип с id {types.oldTypeId} не найден"
        )
    current_animal_types = types_crud.get_animal_types_by_animal_id(animalId)
    if old_type not in current_animal_types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не имеет типа с id {types.oldTypeId}"
        )
    if new_type in current_animal_types:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Животное с id {animalId} уже имеет тип с id {types.newTypeId}"
        )
    animal = animal_crud.update_animal_type(
        new=new_type,
        old=old_type,
        animalId=animalId
    )
    return animal

@router.delete("/{animalId}/types/{typeId}", response_model=Animal)
def delete_animal_type(
    animalId: int = Path(..., ge=1),
    typeId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    types_crud = AnimalTypeCRUD(db)
    db_type = types_crud.get_animal_type_by_id(typeId)
    if not db_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Тип с id {typeId} не найден"
        )
    animal_types = types_crud.get_animal_types_by_animal_id(animalId)
    if db_type not in animal_types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не имеет типа с id {typeId}"
        )
    types_count = animal_crud.get_animal_types_count(animalId)
    if types_count == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"У животного только один тип и это тип с typeId {typeId}"
        )
    return animal_crud.delete_animal_type(
        animalId=animalId,
        typeId=typeId
    )


@router.get("/{animalId}/locations", response_model=List[AnimalLocation])
def get_animal_locations(
    animalId: int = Path(..., ge=1),
    startDateTime: ISODateTime = None,
    endDateTime: ISODateTime = None,
    from_: int = Query(0, ge=0, alias="from"),
    size: int = Query(10, ge=1),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    locations = animal_crud.get_animal_locations(
        animalId=animalId,
        startDateTime=startDateTime,
        endDateTime=endDateTime,
        from_=from_,
        size=size
    )

    return locations


@router.post("/{animalId}/types/{typeId}", response_model=Animal, status_code=status.HTTP_201_CREATED)
def add_animal_type(
    animalId: int = Path(..., ge=1),
    typeId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    types_crud = AnimalTypeCRUD(db)
    db_type = types_crud.get_animal_type_by_id(typeId)
    if not db_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Тип с id {typeId} не найден"
        )
    animal_types = types_crud.get_animal_types_by_animal_id(animalId)
    if db_type in animal_types:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Животное с id {animalId} уже имеет тип с id {typeId}"
        )
    animal_type = animal_crud.add_animal_type(
        animalId=animalId,
        typeId=typeId
    )
    return animal_type.animal


@router.put("/{animalId}/locations", response_model=AnimalLocation)
def update_animal_location(
    locationData: UpdateAnimalLocation,
    animalId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True, is_chipper=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    new_location_point = PointCRUD(db).get_point_by_id(
        locationData.locationPointId)
    if not new_location_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Точка с id {locationData.locationPointId} не найдена"
        )
    location = animal_crud.get_animal_location_by_id(
        locationData.visitedLocationPointId)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Объект с информацией о посещенной точке локации {locationData.visitedLocationPointId} не найден"
        )
    if location.locationPointId == locationData.locationPointId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя изменить точку локации на ту же самую"
        )
    if location.animalId != animalId:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не посещало точку локации с id {locationData.visitedLocationPointId}"
        )
    first_location = animal_crud.get_first_animal_location(animalId)
    chipping_location = PointCRUD(db).get_point_by_id(
        animal.chippingLocationId)
    if locationData.visitedLocationPointId == first_location.id and locationData.locationPointId == chipping_location.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя изменить первую точку на точку чипирования"
        )
    allow_update = animal_crud.check_allow_update_location(
        visitedLocationPoint=location,
        new_location_id=locationData.locationPointId
    )
    if not allow_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя обновлять точку локации на точку, совпадающую со следующей и/или с предыдущей точками"
        )
    return animal_crud.update_animal_location(
        animalLocation=location,
        new_location_id=locationData.locationPointId
    )


@router.delete("/{animalId}/locations/{visitedPointId}", response_model=None)
def delete_animal_location(
    animalId: int = Path(..., ge=1),
    visitedPointId: int = Path(..., ge=1),
    authorize: Authorize = Depends(Authorize(is_admin=True)),
    db: Session = Depends(get_db)
):
    animal_crud = AnimalCRUD(db)
    animal = animal_crud.get_animal_by_id(animalId)
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Животное с id {animalId} не найдено"
        )
    visited_point = animal_crud.get_animal_location_by_id(visitedPointId)
    if not visited_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Объект с информацией о посещенной точке локации с visitedPointId не найден."
        )
    if visited_point.animalId != animalId:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"У животного нет объекта с информацией о посещенной точке локации с visitedPointId"
        )
    fist_location = animal_crud.get_first_animal_location(animalId)
    if fist_location and fist_location.id == visitedPointId:
        second_location = animal_crud.get_animal_location_by_offset(
            animalId, 1)
        if second_location and second_location.locationPointId == animal.chippingLocationId:
            animal_crud.delete(second_location)
    animal_crud.delete(visited_point)



