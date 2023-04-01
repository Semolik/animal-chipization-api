from pydantic import BaseSettings
import os
from app.models.user import UserRoles


class Settings(BaseSettings):
    DATABASE_URI: str = f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    INITIAL_USERS: list[dict] = [
        {
            "id": 1,
            "firstName": "adminFirstName",
            "lastName": "adminLastName",
            "email": "admin@simbirsoft.com",
            "password": "qwerty123",
            "role": UserRoles.ADMIN
        },
        {
            "id": 2,
            "firstName": "chipperFirstName",
            "lastName": "chipperLastName",
            "email": "chipper@simbirsoft.com",
            "password": "qwerty123",
            "role": UserRoles.CHIPPER
        },
        {
            "id": 3,
            "firstName": "userFirstName",
            "lastName": "userLastName",
            "email": "user@simbirsoft.com",
            "password": "qwerty123",
            "role": UserRoles.USER
        }
    ]


settings = Settings()
