from pydantic import BaseModel

from app.schemas.locations import LocationBase


class CreateArea(BaseModel):
    name: str
    areaPoints: list[LocationBase]


class Area(CreateArea):
    id: int

    class Config:
        orm_mode = True
