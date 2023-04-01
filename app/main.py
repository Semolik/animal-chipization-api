
from fastapi import FastAPI
from app.api.api import api_router
from fastapi import Request

from app.db.init import init_db

main_router = FastAPI()


@main_router.middleware("http")
async def modify_response(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 422:
        response.status_code = 400
    return response


@main_router.on_event("startup")
def startup():
    init_db()


main_router.include_router(api_router)
