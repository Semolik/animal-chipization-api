import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.models.user import *
from app.models.animals import *
from app.models.points import *


engine = create_engine(
    f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
)

Base.metadata.create_all(engine)


SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)
