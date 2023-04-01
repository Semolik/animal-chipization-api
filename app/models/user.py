from app.db.base_class import Base
from sqlalchemy import Column, Integer, String, Enum
from enum import Enum as _Enum


class UserRoles(_Enum):
    ADMIN = "ADMIN"
    CHIPPER = "CHIPPER"
    USER = "USER"


class User(Base):
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    firstName = Column(String, nullable=True)
    lastName = Column(String, nullable=True)
    email = Column(String, nullable=False)
    hashed_password = Column(String, index=True, nullable=False)
    role = Column(Enum(UserRoles), default=UserRoles.USER)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRoles.ADMIN

    @property
    def is_chipper(self) -> bool:
        return self.role == UserRoles.CHIPPER

    @property
    def is_user(self) -> bool:
        return self.role == UserRoles.USER
    