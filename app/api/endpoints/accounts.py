from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from app.db.db import get_db
from app.helpers.auth_helper import Authorize
from app.schemas.user import Register, User
from app.crud.crud_user import UserCRUD
from sqlalchemy.orm import Session
from app.models.user import User as UserModel

router = APIRouter(tags=["Аккаунты"], prefix="/accounts")


@router.get("/search", response_model=List[User])
def search_accounts(
    firstName: str = None,
    lastName: str = None,
    email: str = None,
    from_: int = Query(0, ge=0, alias="from"),
    size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(Authorize(test_if_header_exsits=True))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")

    return UserCRUD(db).search_users(
        firstName=firstName,
        lastName=lastName,
        email=email,
        from_=from_,
        size=size
    )


@router.get("/{accountId}", response_model=User)
def get_account(
    accountId: int = Path(ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(Authorize(test_if_header_exsits=True))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    db_user = UserCRUD(db).get_user_by_id(accountId)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Пользователь не найден")

    return db_user


@router.put("/{accountId}", response_model=User)
def update_account(
    user_data: Register,
    accountId: int = Path(ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    db_user = UserCRUD(db).get_user_by_id(accountId)
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    if not db_user or db_user.id != authorized_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Обновление не своего аккаунта или Аккаунт не найден")
    if user_data.email != db_user.email and UserCRUD(db).get_user_by_email(user_data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Аккаунт с таким email уже существует")
    return UserCRUD(db).update_user(
        db_user=db_user,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        email=user_data.email,
        password=user_data.password
    )


@router.delete("/{accountId}", response_model=None)
def delete_account(
    accountId: int = Path(ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    user_crud = UserCRUD(db)
    db_user = user_crud.get_user_by_id(accountId)
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    if not db_user or db_user.id != authorized_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Удаление не своего аккаунта или Аккаунт не найден")
    if not user_crud.is_allow_delete(db_user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Нельзя удалить аккаунт связан с животными")
    user_crud.delete(db_user)
