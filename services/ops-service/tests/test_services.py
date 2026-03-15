from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.models.incidencia import Incidencia
from app.models.calibracion import Calibracion
from app.services import incidencia_service, mantenimiento_service
from app.schemas.incidencia import IncidenciaCreate, IncidenciaUpdate
from app.schemas.mantenimiento import MantenimientoCreate


class TestIncidenciaService:
    def test_auto_create_calibracion_on_finalize(self, db_session):
        """When a correctiva incidencia is finalized, a calibracion incidencia is auto-created."""
        inc = incidencia_service.create_incidencia(
            db_session,
            IncidenciaCreate(
                device_id="T101", tipo="correctiva", prioridad="alta"
            ),
        )
        assert inc.estado == "pendiente"

        updated = incidencia_service.update_incidencia(
            db_session,
            inc.id,
            IncidenciaUpdate(estado="finalizado"),
        )
        assert updated.estado == "finalizado"

        # Verify calibracion incidencia was auto-created
        cal_inc = (
            db_session.query(Incidencia)
            .filter(
                Incidencia.device_id == "T101",
                Incidencia.tipo == "calibracion",
            )
            .first()
        )
        assert cal_inc is not None
        assert cal_inc.prioridad == "alta"

        # Verify calibracion record linked
        cal = (
            db_session.query(Calibracion)
            .filter(Calibracion.incidencia_id == cal_inc.id)
            .first()
        )
        assert cal is not None
        assert cal.device_id == "T101"

    def test_no_auto_calibracion_on_calibracion_finalize(self, db_session):
        """Finalizing a calibracion incidencia should NOT create another calibracion."""
        inc = incidencia_service.create_incidencia(
            db_session,
            IncidenciaCreate(
                device_id="T101", tipo="calibracion", prioridad="media"
            ),
        )
        incidencia_service.update_incidencia(
            db_session,
            inc.id,
            IncidenciaUpdate(estado="finalizado"),
        )

        count = (
            db_session.query(Incidencia)
            .filter(Incidencia.tipo == "calibracion")
            .count()
        )
        assert count == 1  # Only the original one

    def test_evaluate_alerts_creates_incidencias(self, db_session):
        """When ml-service returns >=2 high alerts for a device today, create incidencia."""
        now = datetime.now(timezone.utc).isoformat()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": 1, "device_id": "T101", "nivel_riesgo": "alta",
                    "estado": "activa", "created_at": now,
                },
                {
                    "id": 2, "device_id": "T101", "nivel_riesgo": "alta",
                    "estado": "activa", "created_at": now,
                },
                {
                    "id": 3, "device_id": "T102", "nivel_riesgo": "alta",
                    "estado": "activa", "created_at": now,
                },
            ],
            "total": 3,
        }

        with patch("app.services.incidencia_service.httpx.get", return_value=mock_response):
            created = incidencia_service.evaluate_alerts(
                db_session, "http://ml-service:8002"
            )

        # T101 has 2 alerts -> incidencia created
        # T102 has 1 alert -> no incidencia
        assert len(created) == 1
        assert created[0].device_id == "T101"
        assert created[0].tipo == "correctiva"
        assert created[0].prioridad == "alta"

    def test_evaluate_alerts_no_duplicate(self, db_session):
        """If incidencia already exists today for device, don't create another."""
        incidencia_service.create_incidencia(
            db_session,
            IncidenciaCreate(
                device_id="T101", tipo="correctiva", prioridad="alta"
            ),
        )

        now = datetime.now(timezone.utc).isoformat()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"id": 1, "device_id": "T101", "nivel_riesgo": "alta",
                 "estado": "activa", "created_at": now},
                {"id": 2, "device_id": "T101", "nivel_riesgo": "alta",
                 "estado": "activa", "created_at": now},
            ],
            "total": 2,
        }

        with patch("app.services.incidencia_service.httpx.get", return_value=mock_response):
            created = incidencia_service.evaluate_alerts(
                db_session, "http://ml-service:8002"
            )

        assert len(created) == 0


class TestRepuestosAndProveedores:
    def test_list_repuestos(self, client):
        resp = client.get("/api/v1/repuestos")
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    def test_list_repuestos_by_category(self, client):
        resp = client.get("/api/v1/repuestos?categoria=Sensores%20y%20Detectores")
        assert resp.status_code == 200
        for r in resp.json():
            assert r["categoria"] == "Sensores y Detectores"

    def test_list_proveedores(self, client):
        resp = client.get("/api/v1/proveedores")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2


class TestUsuarios:
    def test_list_usuarios(self, client):
        resp = client.get("/api/v1/usuarios")
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    def test_create_usuario(self, client):
        resp = client.post("/api/v1/usuarios", json={
            "email": "nuevo@oefa.gob.pe",
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "rol": "tecnico",
        })
        assert resp.status_code == 201
        assert resp.json()["email"] == "nuevo@oefa.gob.pe"

    def test_create_usuario_duplicate_email(self, client):
        resp = client.post("/api/v1/usuarios", json={
            "email": "admin@test.com",
            "nombre": "Dup",
            "apellido": "Test",
            "rol": "tecnico",
        })
        assert resp.status_code == 409

    def test_get_usuario(self, client):
        resp = client.get("/api/v1/usuarios/1")
        assert resp.status_code == 200
        assert resp.json()["rol"] == "administrador"

    def test_get_usuario_not_found(self, client):
        resp = client.get("/api/v1/usuarios/999")
        assert resp.status_code == 404
