from typing import List
from fastapi import HTTPException, Header

from sqlalchemy.orm import Session
from app.crud.crud_user import UserCRUD
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import base64
from app.db.db import get_db
from app.models.user import User
security = HTTPBasic()


class Authorize:
    def __init__(self, error_on_unauthorized: bool = True, test_if_header_exsits: bool = False, db: Session = Depends(get_db)):
        self.error_on_unauthorized = error_on_unauthorized
        self.test_if_header_exsits = test_if_header_exsits
        self.db = db

    def __call__(self, Authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
        """
        Авторизация пользователя по логину и паролю в заголовке Authorization в формате Basic base64(login:password)
        """
        error_data = {
            "status_code": status.HTTP_401_UNAUTHORIZED,
            "detail": "Неверные авторизационные данные",
            "headers": {"WWW-Authenticate": "Basic"},
        }
        if not Authorization:
            if self.test_if_header_exsits:
                return True
            if not self.error_on_unauthorized:
                return None
            raise HTTPException(**error_data)
        if not Authorization.startswith("Basic "):
            if not self.error_on_unauthorized:
                return None
            raise HTTPException(**error_data)
        encoded_str = Authorization.replace("Basic ", "")
        auth_data = base64.b64decode(encoded_str).decode("utf-8")
        auth_params = auth_data.split(":")
        if len(auth_params) != 2:
            if not self.error_on_unauthorized:
                return None
            raise HTTPException(**error_data)
        login, password = auth_params
        db_user = UserCRUD(db).login(email=login, password=password)
        if not db_user:
            if not self.error_on_unauthorized:
                return None
            raise HTTPException(**error_data)
        return db_user
