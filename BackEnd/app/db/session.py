from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

_engine: Engine | None = None
SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine, SessionLocal
    if _engine is None:
        _engine = create_engine(settings.DB_URL, future=True)

        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
            class_=Session,
            future=True,
        )
    return _engine


def get_db() -> Session:

    global SessionLocal
    if SessionLocal is None:
        get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
