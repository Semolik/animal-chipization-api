from pydantic import BaseModel, EmailStr

from app.schemas.types import NotEmtyOrWhitespased


class UserBase(BaseModel):
    firstName: NotEmtyOrWhitespased
    lastName: NotEmtyOrWhitespased
    email: EmailStr


class Register(UserBase):
    password: NotEmtyOrWhitespased


class User(UserBase):
    id: int

    class Config:
        orm_mode = True
