from app.db.base_class import Base
from sqlalchemy import Column, Integer,  ForeignKey, String
from sqlalchemy.orm import relationship


class Area(Base):
    __tablename__ = "areas"
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    name = Column(String, nullable=False)
    areaPoints = relationship("Point", secondary="area_point")

class AreaPoint(Base):
    __tablename__ = "area_point"
    area_id = Column(Integer, ForeignKey('areas.id', ondelete="CASCADE"), primary_key=True)
    point_id = Column(Integer, ForeignKey('point.id'), primary_key=True)


