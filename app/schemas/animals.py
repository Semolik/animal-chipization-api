from fastapi import Query
from pydantic import BaseModel, validator
from app.models.animals import AnimalGender, AnimalAlive

from app.schemas.types import ISODateTime, NotEmtyOrWhitespased


class AnimalTypeBase(BaseModel):
    type: NotEmtyOrWhitespased


class AnimalType(AnimalTypeBase):
    id: int

    class Config:
        orm_mode = True


class AnimalBase(BaseModel):
    weight: float = Query(..., gt=0)
    height: float = Query(..., gt=0)
    length: float = Query(..., gt=0)
    gender: AnimalGender
    chipperId: int = Query(..., ge=1)
    chippingLocationId: int = Query(..., ge=1)

    class Config:
        orm_mode = True


class AnimalCreate(AnimalBase):
    animalTypes: list[int] = Query(..., min_items=1)

    @validator('animalTypes')
    def validate_animal_types(cls, v):
        if not v:
            raise ValueError('Список типов животных не может быть пустым')
        if len(v) == 0:
            raise ValueError('Список типов животных не может быть пустым')
        if not all(isinstance(i, int) and i > 0 for i in v):
            raise ValueError(
                'Все типы животных должны быть положительными целыми числами')
        return v

    class Config:
        orm_mode = True


class UpdateAnimal(AnimalBase):
    lifeStatus: AnimalAlive
    chipperId: int = Query(..., ge=1)
    chippingLocationId: int = Query(..., ge=1)


class Animal(AnimalBase):
    id: int
    lifeStatus: AnimalAlive
    chippingDateTime: ISODateTime
    deathDateTime: ISODateTime = None
    visitedLocations: list[int]
    animalTypes: list[int]

    class Config:
        orm_mode = True


class AnimalLocation(BaseModel):
    id: int
    dateTimeOfVisitLocationPoint: ISODateTime
    locationPointId: int

    class Config:
        orm_mode = True


class UpdateAnimalType(BaseModel):
    oldTypeId: int = Query(..., ge=1)
    newTypeId: int = Query(..., ge=1)


class UpdateAnimalLocation(BaseModel):
    visitedLocationPointId: int = Query(..., ge=1)
    locationPointId: int = Query(..., ge=1)
