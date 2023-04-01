from app.crud.crud_user import UserCRUD
from app.db.session import SessionLocal
from app.core.config import settings
from app.models.user import User


def init_db() -> None:
    """Добавление начальных данных"""
    session = SessionLocal()
    for user in settings.INITIAL_USERS:
        user_crud = UserCRUD(session)
        email = user.get("email")
        if not user_crud.get_user_by_email(email):
            user_crud.create_user(
                firstName=user.get("firstName"),
                lastName=user.get("lastName"),
                email=email,
                password=user.get("password"),
                role=user.get("role"),
            )
    session.close()
