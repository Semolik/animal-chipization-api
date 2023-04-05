import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base_class import Base
from app.models.user import *
from app.models.animals import *
from app.models.points import *
from app.models.areas import *


engine = create_engine(settings.DATABASE_URI)
# Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)


SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)
