from app.db.base import CRUDBase
from app.models.animals import AnimalType, AnimalTypeAnimal


class AnimalTypeCRUD(CRUDBase):
    def get_animal_type_by_id(self, id: int) -> AnimalType | None:
        return self.db.query(AnimalType).filter(AnimalType.id == id).first()

    def get_animal_type_by_name(self, name: str) -> AnimalType | None:
        return self.db.query(AnimalType).filter(AnimalType.type == name).first()

    def get_animal_types_by_animal_id(self, animalId: int) -> list[AnimalType]:
        return self.db.query(AnimalType).join(AnimalTypeAnimal).filter(AnimalTypeAnimal.animal_id == animalId).all()

    def create_animal_type(self, name: str) -> AnimalType:
        animal_type = AnimalType(type=name)
        return self.create(animal_type)

    def update_animal_type(self, db_animal_type: AnimalType, name: str) -> AnimalType:
        db_animal_type.type = name
        return self.update(db_animal_type)

    def is_allow_delete_animal_type(self, db_animal_type: AnimalType) -> bool:
        return self.db.query(AnimalTypeAnimal).filter(AnimalTypeAnimal.type_id == db_animal_type.id).first() is None
