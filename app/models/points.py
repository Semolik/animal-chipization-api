from app.db.base_class import Base
from sqlalchemy import Column, Integer, FLOAT


class Point(Base):
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    latitude = Column(FLOAT, nullable=False)
    longitude = Column(FLOAT, nullable=False)

