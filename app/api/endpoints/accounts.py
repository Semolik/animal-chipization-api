from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from app.db.db import get_db
from app.core.auth import Authorize
from app.schemas.user import Register, User, RegisterForAdmin
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
    authorize: Authorize = Depends(Authorize(is_admin=True)),
    db: Session = Depends(get_db)
):
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
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):
    if authorize.current_user_id != accountId and not authorize.current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Нет доступа к аккаунту")
    db_user = UserCRUD(db).get_user_by_id(accountId)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Пользователь не найден")

    return db_user


@router.put("/{accountId}", response_model=User)
def update_account(
    user_data: RegisterForAdmin,
    accountId: int = Path(ge=1),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):
    if authorize.current_user_id != accountId and not authorize.current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Нет доступа к аккаунту")
    user_crud = UserCRUD(db)
    db_user = user_crud.get_user_by_id(accountId)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Пользователь не найден")
    if user_data.email != db_user.email and user_crud.get_user_by_email(user_data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Аккаунт с таким email уже существует")
    return user_crud.update_user(
        db_user=db_user,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        email=user_data.email,
        password=user_data.password,
        role=user_data.role
    )


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_account(
    user_data: RegisterForAdmin,
    authorize: Authorize = Depends(Authorize(is_admin=True)),
    db: Session = Depends(get_db)
):
    user_crud = UserCRUD(db)
    if user_crud.get_user_by_email(user_data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Аккаунт с таким email уже существует")
    return user_crud.create_user(
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        email=user_data.email,
        password=user_data.password,
        role=user_data.role
    )


@router.delete("/{accountId}")
def delete_account(
    accountId: int = Path(ge=1),
    authorize: Authorize = Depends(Authorize()),
    db: Session = Depends(get_db)
):

    if authorize.current_user_id != accountId and not authorize.current_user.is_admin:
        print(accountId, authorize.current_user_id, authorize.current_user)
        print(authorize.current_user_id != accountId, not authorize.current_user.is_admin)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Нет доступа к аккаунту")
    user_crud = UserCRUD(db)
    db_user = user_crud.get_user_by_id(accountId)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Пользователь не найден")
    if not user_crud.is_allow_delete(db_user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Нельзя удалить аккаунт связан с животными")
    user_crud.delete(db_user)
