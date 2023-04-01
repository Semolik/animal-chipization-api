from datetime import datetime
from app.db.base import CRUDBase
from app.models.animals import AnimalAlive, AnimalGender, AnimalType, Animal, AnimalTypeAnimal, AnimalLocation
from app.models.points import Point


class AnimalCRUD(CRUDBase):

    def get_animal_visited_locations_by_animal_id(self, animalId: int) -> list[AnimalLocation]:
        return self.db.query(Point).join(AnimalLocation).filter(AnimalLocation.animalId == animalId).all()

    def get_animal_by_id(self, id: int) -> Animal | None:
        return self.db.query(Animal).filter(Animal.id == id).first()

    def get_last_animal_location(self, animalId: int) -> AnimalLocation | None:
        return self.db.query(AnimalLocation).filter(AnimalLocation.animalId == animalId).order_by(AnimalLocation.dateTimeOfVisitLocationPoint.desc()).first()

    def get_animal_chipping_location(self, animalId: int) -> Point | None:
        return self.db.query(Point).join(Animal).filter(Animal.id == animalId).order_by(Animal.chippingDateTime.desc()).first()

    def get_first_animal_location(self, animalId: int) -> AnimalLocation | None:
        return self.get_animal_location_by_offset(animalId, 0)

    def get_animal_location_by_offset(self, animalId: int, offset: int) -> AnimalLocation | None:
        return self.db.query(AnimalLocation).filter(AnimalLocation.animalId == animalId).order_by(AnimalLocation.dateTimeOfVisitLocationPoint.asc()).offset(offset).first()

    def get_animal_location_by_id(self, id: int) -> AnimalLocation | None:
        return self.db.query(AnimalLocation).filter(AnimalLocation.id == id).first()

    def update_animal_location(self, animalLocation: AnimalLocation, new_location_id: int) -> AnimalLocation:
        animalLocation.locationPointId = new_location_id
        return self.update(animalLocation)

    def update_animal(self, animal: Animal, weight: int, length: int, height: int, gender: AnimalGender, chipperId: int, chippingLocationId: int, lifeStatus: AnimalAlive) -> Animal:
        animal.weight = weight
        animal.length = length
        animal.height = height
        animal.gender = gender
        animal.lifeStatus = lifeStatus
        animal.chipperId = chipperId
        animal.chippingLocationId = chippingLocationId
        if lifeStatus == AnimalAlive.DEAD and animal.deathDateTime is None:
            animal.deathDateTime = datetime.now()
        return self.update(animal)

    def get_animal_has_location(self, animalId: int, locationId: int) -> bool:
        return self.db.query(AnimalLocation).filter(AnimalLocation.animalId == animalId, AnimalLocation.locationPointId == locationId).first() is not None

    def get_animal_has_visited_point(self, animalId: int, visitedLocationPointId: int) -> bool:
        return self.db.query(AnimalLocation).filter(AnimalLocation.animalId == animalId, AnimalLocation.id == visitedLocationPointId).first() is not None

    def check_allow_update_location(self, visitedLocationPoint: AnimalLocation, new_location_id: int) -> bool:
        prev = self.db.query(AnimalLocation).filter(
            AnimalLocation.animalId == visitedLocationPoint.animalId,
            AnimalLocation.dateTimeOfVisitLocationPoint < visitedLocationPoint.dateTimeOfVisitLocationPoint
        ).order_by(AnimalLocation.dateTimeOfVisitLocationPoint.desc()).first()
        next = self.db.query(AnimalLocation).filter(
            AnimalLocation.animalId == visitedLocationPoint.animalId,
            AnimalLocation.dateTimeOfVisitLocationPoint > visitedLocationPoint.dateTimeOfVisitLocationPoint
        ).order_by(AnimalLocation.dateTimeOfVisitLocationPoint.asc()).first()
        if prev is None and next is None:
            return True
        if prev is None:
            return next.locationPointId != new_location_id
        if next is None:
            return prev.locationPointId != new_location_id
        return prev.locationPointId != new_location_id and next.locationPointId != new_location_id

    def get_animal_locations_count(self, animalId: int):
        return self.db.query(AnimalLocation).filter(AnimalLocation.animalId == animalId).count()

    def get_animal_locations(self, animalId: int, startDateTime: datetime, endDateTime: datetime, from_: int, size: int) -> list[AnimalLocation] | None:
        query = self.db.query(AnimalLocation).filter(
            AnimalLocation.animalId == animalId)
        if startDateTime:
            query = query.filter(
                AnimalLocation.dateTimeOfVisitLocationPoint >= startDateTime)
        if endDateTime:
            query = query.filter(
                AnimalLocation.dateTimeOfVisitLocationPoint <= endDateTime)
        query = query.order_by(
            AnimalLocation.dateTimeOfVisitLocationPoint.asc())
        query = query.slice(from_, from_ + size)
        return query.all()

    def search_animals(self, startDateTime: datetime, endDateTime: datetime, chipperId: int, lifeStatus: AnimalAlive, gender: AnimalGender, from_: int, size: int) -> list[Animal] | None:
        query = self.db.query(Animal)
        if startDateTime:
            query = query.filter(
                Animal.chippingDateTime >= startDateTime)
        if endDateTime:
            query = query.filter(
                Animal.chippingDateTime <= endDateTime)
        if chipperId:
            query = query.filter(
                Animal.chipperId == chipperId)
        if lifeStatus:
            query = query.filter(
                Animal.lifeStatus == lifeStatus)
        if gender:
            query = query.filter(Animal.gender == gender)
        query = query.order_by(
            Animal.chippingDateTime.asc())
        query = query.slice(from_, from_ + size)
        return query.all()

    def create_animal(
        self,
            types: list[AnimalType],
            weight: float,
            length: float,
            height: float,
            gender: AnimalGender,
            chipperId: int,
            chippingLocationId: int
    ) -> Animal:
        animal = self.create(
            Animal(
                weight=weight,
                length=length,
                height=height,
                gender=gender,
                chipperId=chipperId,
                chippingLocationId=chippingLocationId
            )
        )
        for animal_type in types:
            self.create(
                AnimalTypeAnimal(
                    animal_id=animal.id,
                    type_id=animal_type.id
                )
            )
        return animal

    def add_animal_location(self, animalId: int, locationPointId: int) -> AnimalLocation:
        return self.create(
            AnimalLocation(
                animalId=animalId,
                locationPointId=locationPointId,
            )
        )

    def add_animal_type(self, animalId: int, typeId: int) -> AnimalTypeAnimal:
        return self.create(
            AnimalTypeAnimal(
                animal_id=animalId,
                type_id=typeId
            )
        )

    def update_animal_type(self, new: AnimalType, old: AnimalType, animalId: int) -> Animal:
        animal = self.delete_animal_type(animalId, old.id)
        self.add_animal_type(animalId, new.id)
        return animal

    def get_animal_types_count(self, animalId: int):
        return self.db.query(AnimalTypeAnimal).filter(AnimalTypeAnimal.animal_id == animalId).count()

    def delete_animal_type(self, animalId: int, typeId: int):
        model = self.db.query(AnimalTypeAnimal).filter(AnimalTypeAnimal.animal_id ==
                                                       animalId, AnimalTypeAnimal.type_id == typeId).first()
        animal = model.animal
        self.delete(model)
        return animal
