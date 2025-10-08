from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DB_PATH
from .models import Base

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
