import os

# Apagar el scheduler en tests (no arrancar hilos de fondo).
# Debe fijarse ANTES de importar app.main / app.scheduler.
os.environ.setdefault("WATCHDOG_ENABLED", "0")
os.environ.setdefault("METRICS_ENABLED", "0")
os.environ.setdefault("THETA_RECAL_ENABLED", "0")
os.environ.setdefault("RETRAIN_CHECK_ENABLED", "0")
os.environ.setdefault("AUTOCLOSE_ENABLED", "0")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from shared.models.base import Base
from app.models.health_state import HealthReading, HealthDeviceState  # noqa: F401
from app.models.model_metric import ModelMetric  # noqa: F401
from app.main import app
from app.database import get_db

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
