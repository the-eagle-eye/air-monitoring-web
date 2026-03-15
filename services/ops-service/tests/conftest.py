import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from shared.models.base import Base
from app.models.datalogger import Datalogger  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
from app.models.proveedor_calibracion import ProveedorCalibracion  # noqa: F401
from app.models.repuesto import Repuesto  # noqa: F401
from app.models.incidencia import Incidencia  # noqa: F401
from app.models.mantenimiento import MantenimientoCorrectivo  # noqa: F401
from app.models.mantenimiento import MantenimientoRepuesto  # noqa: F401
from app.models.calibracion import Calibracion  # noqa: F401
from app.models.archivo_adjunto import ArchivoAdjunto  # noqa: F401
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
    db = TestingSessionLocal()
    # Seed test data
    if not db.query(Usuario).first():
        db.add_all([
            Usuario(
                email="admin@test.com", nombre="Admin", apellido="Test",
                rol="administrador",
            ),
            Usuario(
                email="tecnico@test.com", nombre="Tecnico", apellido="Test",
                rol="tecnico",
            ),
            Usuario(
                email="coord@test.com", nombre="Coordinador", apellido="Test",
                rol="coordinador",
            ),
        ])
        db.add_all([
            ProveedorCalibracion(nombre="Proveedor Test 1"),
            ProveedorCalibracion(nombre="Proveedor Test 2"),
        ])
        db.add_all([
            Repuesto(nombre="Sensor SO2", categoria="Sensores y Detectores"),
            Repuesto(nombre="Filtro PTFE", categoria="Filtros y Consumibles"),
            Repuesto(nombre="Bomba de vacio", categoria="Bombas y Sistemas de Muestreo"),
        ])
        db.add(Datalogger(
            nombre="CR310 Test", codigo_interno="DL-TEST-001",
            numero_serie="SN-TEST", ubicacion="Lab Test",
        ))
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
