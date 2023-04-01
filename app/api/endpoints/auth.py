from fastapi import APIRouter, Depends, HTTPException, status
from app.db.db import get_db
from app.core.auth import Authorize
from app.schemas.user import Register, User
from app.crud.crud_user import UserCRUD
from sqlalchemy.orm import Session
from app.models.user import User as UserModel

router = APIRouter(tags=["Авторизация"])


@router.post("/registration", response_model=User, status_code=status.HTTP_201_CREATED)
def registration(
    user: Register,
    authorize: Authorize = Depends(Authorize(required=False))
):
    if authorize.current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Пользователь уже авторизован")
    user_crud = UserCRUD(authorize.db)
    if user_crud.get_user_by_email(user.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Пользователь с таким email уже существует")
    return user_crud.create_user(
        firstName=user.firstName,
        lastName=user.lastName,
        email=user.email,
        password=user.password,
    )
