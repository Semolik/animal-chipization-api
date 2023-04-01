from app.db.base_class import Base
from sqlalchemy import Column, Integer, FLOAT, String, Enum, ForeignKey, DateTime, func, event
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

import enum


class AnimalGender(enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class AnimalAlive(enum.Enum):
    ALIVE = "ALIVE"
    DEAD = "DEAD"


class AnimalType(Base):
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    type = Column(String, nullable=False)


class Animal(Base):
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    weight = Column(FLOAT, nullable=False)
    height = Column(FLOAT, nullable=False)
    length = Column(FLOAT, nullable=False)
    gender = Column(Enum(AnimalGender), nullable=False)
    lifeStatus = Column(Enum(AnimalAlive), nullable=False,
                        default=AnimalAlive.ALIVE)
    chippingDateTime = Column(DateTime(timezone=True),
                              nullable=False, default=func.now())
    chipperId = Column(Integer, ForeignKey("user.id"), nullable=False)
    chippingLocationId = Column(
        Integer, ForeignKey("point.id"), nullable=False)
    deathDateTime = Column(DateTime(
        timezone=True
    ))
    AnimalTypes = relationship(
        "AnimalType", secondary="animaltypeanimal", primaryjoin="Animal.id == AnimalTypeAnimal.animal_id")
    VisitedLocations = relationship(
        "AnimalLocation", primaryjoin="Animal.id == AnimalLocation.animalId")

    @hybrid_property
    def visitedLocations(self):
        return [location.id for location in self.VisitedLocations]

    @hybrid_property
    def animalTypes(self):
        return [animal_type.id for animal_type in self.AnimalTypes]


class AnimalTypeAnimal(Base):
    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey(AnimalType.id), nullable=False)
    animal_id = Column(Integer, ForeignKey(Animal.id), nullable=False)
    animal = relationship(Animal, foreign_keys=[
                          animal_id], overlaps="AnimalTypes")


class AnimalLocation(Base):
    id = Column(Integer, primary_key=True, index=True)
    dateTimeOfVisitLocationPoint = Column(
        DateTime(timezone=True), server_default=func.now())
    locationPointId = Column(Integer, ForeignKey('point.id'), nullable=False)
    animalId = Column(Integer, ForeignKey(Animal.id), nullable=False)
    animal = relationship(Animal, foreign_keys=[
                          animalId], overlaps="VisitedLocations")
