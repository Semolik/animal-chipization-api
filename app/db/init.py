from app.crud.crud_user import UserCRUD
from app.db.session import SessionLocal
from app.core.config import settings
from app.models.user import User
import time

def init_db() -> None:
    """Добавление начальных данных"""
    session = SessionLocal()
    for user in settings.INITIAL_USERS:

        user_crud = UserCRUD(session)
        password_hash = user_crud.get_password_hash(user.get("password"))
        user = User(
            firstName=user.get("firstName"),
            lastName=user.get("lastName"),
            email=user.get("email"),
            hashed_password=password_hash,
            role=user.get("role")
        )
        session.add(user)

    session.flush()
    session.commit()
    time.sleep(3)
