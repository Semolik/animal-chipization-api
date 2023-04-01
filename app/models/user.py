from app.db.base_class import Base
from sqlalchemy import Column, Integer, String


class User(Base):
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    firstName = Column(String, nullable=True)
    lastName = Column(String, nullable=True)
    email = Column(String, nullable=False)
    hashed_password = Column(String, index=True, nullable=False)
