from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Create standard SQL database engine
engine = create_engine(
    settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20
)

# Create session maker session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Declarative base model class
class Base(DeclarativeBase):
    pass


# Dependency injection generator for route handlers
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
