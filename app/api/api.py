from fastapi import APIRouter
from app.api.endpoints import auth, accounts, locations
from app.api.endpoints.animals import animals
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(animals.router)
api_router.include_router(locations.router)
