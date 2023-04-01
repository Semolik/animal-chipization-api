from fastapi import Query
from pydantic import BaseModel


class LocationBase(BaseModel):
    latitude: float = Query(..., ge=-90, le=90)
    longitude: float = Query(..., ge=-180, le=180)

    class Config:
        orm_mode = True


class Location(LocationBase):
    id: int

    class Config:
        orm_mode = True
