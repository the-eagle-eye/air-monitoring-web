from shared.database import get_engine, get_session_factory
from app.config import settings

engine = get_engine(settings.DATABASE_URL)
SessionLocal = get_session_factory(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
