from fastapi import APIRouter, Depends, HTTPException, Path, status
from app.core.areas import AreaValidator
from app.db.db import get_db
from app.core.auth import Authorize
from sqlalchemy.orm import Session
from app.schemas.areas import Area, CreateArea
router = APIRouter(tags=["Зоны"], prefix="/areas")


@router.post("", response_model=Area, status_code=status.HTTP_201_CREATED)
def create_location(
    area_data: CreateArea,
    authorize: Authorize = Depends(Authorize(is_admin=True)),
    db: Session = Depends(get_db)
):
    if not AreaValidator(area_data.areaPoints).validate():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Неверные координаты")
