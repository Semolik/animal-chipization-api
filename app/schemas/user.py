from pydantic import BaseModel, EmailStr

from app.models.user import UserRoles
from app.schemas.types import NotEmtyOrWhitespased


class UserBase(BaseModel):
    firstName: NotEmtyOrWhitespased
    lastName: NotEmtyOrWhitespased
    email: EmailStr


class Register(UserBase):
    password: NotEmtyOrWhitespased


class RegisterForAdmin(Register):
    role: UserRoles


class User(UserBase):
    id: int
    role: UserRoles

    class Config:
        orm_mode = True
