from fastapi import APIRouter, Depends, HTTPException, Path, status
from app.crud.crud_types import AnimalTypeCRUD
from app.db.db import get_db
from app.helpers.auth_helper import Authorize
from app.schemas.animals import AnimalType, AnimalTypeBase
from app.models.user import User as UserModel
from sqlalchemy.orm import Session

router = APIRouter(tags=["Типы животных"], prefix="/types")


@router.post("", response_model=AnimalType, status_code=status.HTTP_201_CREATED)
def create_animal_type(
    animal_type_data: AnimalTypeBase,
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    animal_type_crud = AnimalTypeCRUD(db)
    animal_type = animal_type_crud.get_animal_type_by_name(
        animal_type_data.type)
    if animal_type:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Тип животного с таким type  уже существует")
    return animal_type_crud.create_animal_type(
        name=animal_type_data.type,
    )


@router.put("/{typeId}", response_model=AnimalType)
def update_animal_type(
    animal_type_data: AnimalTypeBase,
    typeId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    animal_type_crud = AnimalTypeCRUD(db)
    animal_type = animal_type_crud.get_animal_type_by_id(typeId)
    if not animal_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Тип животного не найден")
    animal_type_new_name = animal_type_crud.get_animal_type_by_name(
        animal_type_data.type)
    if animal_type_new_name and animal_type_new_name.id != animal_type.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Тип животного с таким type  уже существует")
    return animal_type_crud.update_animal_type(
        db_animal_type=animal_type,
        name=animal_type_data.type,
    )


@router.delete("/{typeId}", response_model=None)
def delete_animal_type(
    typeId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(
        Authorize(error_on_unauthorized=False))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    animal_type_crud = AnimalTypeCRUD(db)
    animal_type = animal_type_crud.get_animal_type_by_id(typeId)
    if not animal_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Тип животного не найден")
    if not animal_type_crud.is_allow_delete_animal_type(animal_type):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Невозможно удалить тип животного, так как он используется")
    animal_type_crud.delete(animal_type)


@router.get("/{typeId}", response_model=AnimalType)
def get_animal_type(
    typeId: int = Path(10, ge=1),
    db: Session = Depends(get_db),
    authorized_user: UserModel = Depends(Authorize(test_if_header_exsits=True))
):
    if not authorized_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Необходима авторизация")
    animal_type = AnimalTypeCRUD(db).get_animal_type_by_id(typeId)
    if not animal_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Тип животного не найден")
    return animal_type
