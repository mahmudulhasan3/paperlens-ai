import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL is missing in the .env file")

# Database step: one engine for the whole project
engine = create_engine(DATABASE_URL)

# Database step: a factory that creates one session for every request
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Database step: the base class that all table classes will inherit from
class Base(DeclarativeBase):
    pass


# Database step: give one session to a request and always close it afterwards
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
