from app.db.base_class import Base
from sqlalchemy import Column, Integer,  ForeignKey, String, Float
from sqlalchemy.orm import relationship


class Area(Base):
    __tablename__ = "areas"
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    name = Column(String, nullable=False)
    areaPoints = relationship("AreaPoint", primaryjoin="Area.id == AreaPoint.area_id", cascade="all, delete-orphan")


class AreaPoint(Base):
    __tablename__ = "area_point"
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    area_id = Column(Integer, ForeignKey('areas.id'), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    next_id = Column(Integer, ForeignKey('area_point.id'), nullable=True)
    next = relationship("AreaPoint",
                        primaryjoin="AreaPoint.next_id == AreaPoint.id",

                        uselist=False,
                        )


