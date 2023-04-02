from pydantic import BaseModel

from app.schemas.locations import LocationBase


class CreateArea(BaseModel):
    name: str
    areaPoints: list[LocationBase]


class Area(CreateArea):
    id: int

    class Config:
        orm_mode = True


class animalsAnalytic(BaseModel):
    animalType: str
    animalTypeId: int
    quantityAnimals: int
    animalsArrived: int
    animalsGone: int


class AreaAnalytics(BaseModel):
    totalQuantityAnimals: int
    totalAnimalsArrived: int
    totalAnimalsGone: int
    animalsAnalytics: list[animalsAnalytic]
