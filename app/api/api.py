from fastapi import APIRouter
from app.api.endpoints import auth, accounts, locations, areas
from app.api.endpoints.animals import animals, types, locations as animals_locations
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(locations.router)
animals.router.include_router(types.router)
api_router.include_router(animals.router)
api_router.include_router(animals_locations.router)
api_router.include_router(areas.router)

