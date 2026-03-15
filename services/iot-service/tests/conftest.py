import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from shared.models.base import Base
from app.models.equipo import Equipo  # noqa: F401
from app.models.lectura_iot import LecturaIoT  # noqa: F401
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
    """Enable foreign key support in SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Seed test equipment
    db = TestingSessionLocal()
    if not db.query(Equipo).first():
        db.add_all(
            [
                Equipo(device_id="T101", nombre="Analizador #1", tipo="Thermo 450i"),
                Equipo(device_id="T102", nombre="Analizador #2", tipo="Thermo 450i"),
                Equipo(device_id="T103", nombre="Analizador #3", tipo="Thermo 450i"),
            ]
        )
        db.commit()
    db.close()
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


VALID_READING_PAYLOAD = {
    "equipo": "T101",
    "SO2_ppb": 25.43,
    "H2S_ppb": 2.18,
    "Reaction_Temp": 35.0,
    "IZS_Temp": 34.2,
    "PMT_Temp": 36.1,
    "SampleFlow": 452.3,
    "Pressure": 29.76,
    "UVLampIntensity": 403.5,
    "Box_Temp": 33.7,
    "HVPS_V": 671.2,
    "Conv_Temp": 35.9,
    "Ozone_flow": 480.5,
    "timestamp": "2025-10-27 18:30:00",
}
