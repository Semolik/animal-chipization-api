from app.crud.crud_user import UserCRUD
from app.db.session import SessionLocal
from app.core.config import settings
from app.models.user import User


def init_db() -> None:
    """Добавление начальных данных"""
    for user in settings.INITIAL_USERS:
        session = SessionLocal()
        user_crud = UserCRUD(session)
        email = user.get("email")
        if not user_crud.get_user_by_email(email):
            password_hash = user_crud.get_password_hash(user.get("password"))
            user = User(

                firstName=user.get("firstName"),
                lastName=user.get("lastName"),
                email=email,
                hashed_password=password_hash,
                role=user.get("role")
            )
            session.add(user)
            session.commit()
        session.close()
