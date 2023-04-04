import base64
from fastapi import Depends, HTTPException, status,Header
from sqlalchemy.orm import Session
from app.crud.crud_user import UserCRUD
from app.db.db import get_db
from app.models.user import User, UserRoles


class Authorize:
    def __init__(self, required: bool = True,is_admin: bool = False, is_chipper: bool = False):
        self.required = required
        accepted_roles = []
        if is_admin:
            accepted_roles.append(UserRoles.ADMIN)
        if is_chipper:
            accepted_roles.append(UserRoles.CHIPPER)
        if len(accepted_roles) == 0:
            accepted_roles = [UserRoles.ADMIN, UserRoles.CHIPPER, UserRoles.USER]
        self.accepted_roles = accepted_roles

    def __call__(self, Authorization: str | None = Header(default=None, include_in_schema=False),
                 db: Session = Depends(get_db)) -> "Authorize":
        """
        Авторизация пользователя по логину и паролю в заголовке Authorization в формате Basic base64(login:password)
        """
        error_data = {
            "status_code": status.HTTP_401_UNAUTHORIZED,
            "detail": "Неверные авторизационные данные",
            "headers": {"WWW-Authenticate": "Basic"},
        }
        self.current_user = None
        self.current_user_id = None
        self.db = db
        if not Authorization or not Authorization.startswith("Basic "):
            if not self.required:
                return self
            raise HTTPException(**error_data)
        encoded_str = Authorization.replace("Basic ", "")
        auth_data = base64.b64decode(encoded_str).decode("utf-8")
        auth_params = auth_data.split(":")
        if len(auth_params) != 2:
            if not self.required:
                return self
            raise HTTPException(**error_data)
        login, password = auth_params
        db_user = UserCRUD(db).login(email=login, password=password)
        if not db_user:
            if not self.required:
                return self
            raise HTTPException(**error_data)
        self.current_user = db_user
        self.current_user_id = db_user.id
        if db_user.role not in self.accepted_roles:
            if not self.required:
                return self
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Недостаточно прав")
        return self


