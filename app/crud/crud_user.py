from typing import List
from app.crud.base import CRUDBase
from app.models.user import User, UserRoles
from app.models.animals import Animal
from passlib.context import CryptContext


class UserCRUD(CRUDBase):

    def __init__(self, db) -> None:
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def search_users(self, firstName: str, lastName: str, email: str, from_: int, size: int) -> List[User]:
        query = self.db.query(User)
        if firstName is not None:
            query = query.filter(User.firstName.ilike(f"%{firstName}%"))
        if lastName is not None:
            query = query.filter(User.lastName.ilike(f"%{lastName}%"))
        if email is not None:
            query = query.filter(User.email.ilike(f"%{email}%"))
        query = query.order_by(User.id.asc())
        return query.slice(from_, from_ + size).all()

    def create_user(self, firstName: str, lastName: str, email: str, password: str, role: UserRoles = None) -> User:
        password_hash = self.get_password_hash(password)
        user = User(
            firstName=firstName,
            lastName=lastName,
            email=email,
            hashed_password=password_hash,
            role=role
        )
        return self.create(user)

    def is_allow_delete(self, db_user: User) -> bool:
        return self.db.query(Animal).filter(Animal.chipperId == db_user.id).first() is None

    def update_user(self, db_user: User, firstName: str, lastName: str, email: str, password: str, role: UserRoles) -> User:
        db_user.firstName = firstName
        db_user.lastName = lastName
        db_user.email = email
        db_user.hashed_password = self.get_password_hash(password)
        db_user.role = role
        return self.update(db_user)

    def login(self, email: str, password: str) -> User | None:
        db_user = self.get_user_by_email(email=email)
        if not db_user:
            return None
        if not self.pwd_context.verify(password, db_user.hashed_password):
            return None
        return db_user

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def check_password(self, user: User, password: str) -> bool:
        return self.pwd_context.verify(password, user.hashed_password)
