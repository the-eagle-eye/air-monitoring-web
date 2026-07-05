from unittest.mock import patch, MagicMock
from datetime import date, datetime, timedelta, timezone

from app.models.incidencia import Incidencia
from app.models.calibracion import Calibracion
from app.services import incidencia_service, mantenimiento_service, calibracion_service
from app.schemas.incidencia import IncidenciaCreate, IncidenciaUpdate
from app.schemas.calibracion import CalibracionCreate
from app.schemas.mantenimiento import MantenimientoCreate


def _finalizar(db, inc_id):
    """ITIL: transiciona una incidencia por el ciclo válido hasta finalizado
    (pendiente -> en_ejecucion -> resuelto -> finalizado)."""
    for estado in ("en_ejecucion", "resuelto", "finalizado"):
        result = incidencia_service.update_incidencia(
            db, inc_id, IncidenciaUpdate(estado=estado))
    return result


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

        updated = _finalizar(db_session, inc.id)
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
        _finalizar(db_session, inc.id)

        count = (
            db_session.query(Incidencia)
            .filter(Incidencia.tipo == "calibracion")
            .count()
        )
        assert count == 1  # Only the original one


class TestCalibracionDirectCreation:
    def test_create_calibracion_without_incidencia(self, db_session):
        """Creating a calibracion without incidencia_id should NOT auto-create an incidencia."""
        cal = calibracion_service.create_calibracion(
            db_session,
            CalibracionCreate(device_id="T101", nota="Direct calibracion"),
        )
        assert cal.id is not None
        assert cal.incidencia_id is None
        assert cal.device_id == "T101"
        assert cal.estado == "pendiente"

        # Verify NO incidencia was created
        count = db_session.query(Incidencia).count()
        assert count == 0

    def test_create_calibracion_with_incidencia(self, db_session):
        """Creating a calibracion with incidencia_id should link correctly."""
        inc = incidencia_service.create_incidencia(
            db_session,
            IncidenciaCreate(device_id="T101", tipo="calibracion", prioridad="media"),
        )
        cal = calibracion_service.create_calibracion(
            db_session,
            CalibracionCreate(device_id="T101", incidencia_id=inc.id),
        )
        assert cal.incidencia_id == inc.id
        assert cal.estado == "pendiente"

    def test_complete_direct_calibracion_no_incidencia(self, db_session):
        """Completing a direct calibracion should set estado=completada without creating incidencia."""
        from app.schemas.calibracion import CalibracionUpdate
        from datetime import datetime, timezone

        cal = calibracion_service.create_calibracion(
            db_session,
            CalibracionCreate(device_id="T101"),
        )
        assert cal.estado == "pendiente"

        updated = calibracion_service.update_calibracion(
            db_session,
            cal.id,
            CalibracionUpdate(
                fecha_calibracion=datetime.now(timezone.utc),
                nota="Calibracion completada",
                certificado_url="https://cert.pdf",
                proveedor_id=1,
            ),
        )
        assert updated.estado == "completada"
        assert updated.incidencia_id is None

        # Verify NO incidencia was created
        count = db_session.query(Incidencia).count()
        assert count == 0


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
            "password": "nuevo123",
        })
        assert resp.status_code == 201
        assert resp.json()["email"] == "nuevo@oefa.gob.pe"

    def test_create_usuario_duplicate_email(self, client):
        resp = client.post("/api/v1/usuarios", json={
            "email": "admin@test.com",
            "nombre": "Dup",
            "apellido": "Test",
            "rol": "tecnico",
            "password": "duptest123",
        })
        assert resp.status_code == 409

    def test_get_usuario(self, client):
        resp = client.get("/api/v1/usuarios/1")
        assert resp.status_code == 200
        assert resp.json()["rol"] == "administrador"

    def test_get_usuario_not_found(self, client):
        resp = client.get("/api/v1/usuarios/999")
        assert resp.status_code == 404


class TestAutoCalibrationCoordinador:
    @patch("app.services.incidencia_service._fetch_equipo_data")
    @patch("app.services.email_service.send_calibracion_notification")
    def test_auto_calibracion_assigns_coordinador(
        self, mock_email, mock_fetch, db_session
    ):
        """When correctiva finalizes, auto-calibracion is assigned to coordinador."""
        mock_fetch.return_value = {"device_id": "T101"}
        mock_email.return_value = True

        inc = incidencia_service.create_incidencia(
            db_session,
            IncidenciaCreate(device_id="T101", tipo="correctiva", prioridad="alta"),
        )
        _finalizar(db_session, inc.id)

        cal_inc = (
            db_session.query(Incidencia)
            .filter(
                Incidencia.device_id == "T101",
                Incidencia.tipo == "calibracion",
            )
            .first()
        )
        assert cal_inc is not None
        assert cal_inc.responsable_id is not None
        # coordinador is user 3 in seed data
        from app.models.usuario import Usuario
        coord = db_session.get(Usuario, cal_inc.responsable_id)
        assert coord.rol == "coordinador"

    @patch("app.services.incidencia_service._fetch_equipo_data")
    @patch("app.services.email_service.send_calibracion_notification")
    def test_auto_calibracion_sends_email(
        self, mock_email, mock_fetch, db_session
    ):
        """When correctiva finalizes, email notification is sent."""
        mock_fetch.return_value = {"device_id": "T101"}
        mock_email.return_value = True

        inc = incidencia_service.create_incidencia(
            db_session,
            IncidenciaCreate(device_id="T101", tipo="correctiva", prioridad="alta"),
        )
        _finalizar(db_session, inc.id)

        mock_email.assert_called_once()
        call_args = mock_email.call_args
        assert call_args[1].get("motivo", call_args[0][3] if len(call_args[0]) > 3 else None) == "post_correctiva" or call_args.kwargs.get("motivo") == "post_correctiva"


class TestAnnualCalibration:
    def _mock_equipos_response(self, equipos_list):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"items": equipos_list}
        return mock_response

    @patch("app.services.email_service.send_calibracion_notification")
    def test_check_annual_creates_incidencia_in_window(
        self, mock_email, db_session
    ):
        """Equipo with anniversary in 5 days should trigger incidencia creation."""
        mock_email.return_value = True
        today = date.today()
        # fecha_ingreso such that anniversary is in 5 days
        anniversary = today + timedelta(days=5)
        fecha_ingreso = anniversary.replace(year=anniversary.year - 1)

        mock_resp = self._mock_equipos_response([
            {
                "device_id": "T101",
                "nombre": "Analizador SO2",
                "modelo": "T101",
                "marca": "Teledyne",
                "ubicacion": "Lab OEFA",
                "parametro_medicion": "SO2",
                "fecha_ingreso": fecha_ingreso.isoformat(),
            }
        ])

        with patch("app.services.incidencia_service.httpx.get", return_value=mock_resp):
            created = incidencia_service.check_annual_calibrations(
                db_session, "http://iot-service:8001"
            )

        assert len(created) == 1
        assert created[0].device_id == "T101"
        assert created[0].tipo == "calibracion"
        assert "Calibracion anual" in created[0].descripcion

        # Verify calibracion record
        cal = (
            db_session.query(Calibracion)
            .filter(Calibracion.incidencia_id == created[0].id)
            .first()
        )
        assert cal is not None

        # Verify coordinador assigned
        assert created[0].responsable_id is not None

    @patch("app.services.email_service.send_calibracion_notification")
    def test_check_annual_skips_outside_window(
        self, mock_email, db_session
    ):
        """Equipo with anniversary in 60 days should NOT trigger incidencia."""
        today = date.today()
        anniversary = today + timedelta(days=60)
        fecha_ingreso = anniversary.replace(year=anniversary.year - 1)

        mock_resp = self._mock_equipos_response([
            {
                "device_id": "T102",
                "fecha_ingreso": fecha_ingreso.isoformat(),
            }
        ])

        with patch("app.services.incidencia_service.httpx.get", return_value=mock_resp):
            created = incidencia_service.check_annual_calibrations(
                db_session, "http://iot-service:8001"
            )

        assert len(created) == 0
        mock_email.assert_not_called()

    @patch("app.services.email_service.send_calibracion_notification")
    def test_check_annual_skips_null_fecha_ingreso(
        self, mock_email, db_session
    ):
        """Equipo without fecha_ingreso should be skipped."""
        mock_resp = self._mock_equipos_response([
            {"device_id": "T103", "fecha_ingreso": None}
        ])

        with patch("app.services.incidencia_service.httpx.get", return_value=mock_resp):
            created = incidencia_service.check_annual_calibrations(
                db_session, "http://iot-service:8001"
            )

        assert len(created) == 0

    @patch("app.services.email_service.send_calibracion_notification")
    def test_check_annual_idempotent(self, mock_email, db_session):
        """Running check twice should only create one incidencia."""
        mock_email.return_value = True
        today = date.today()
        anniversary = today + timedelta(days=3)
        fecha_ingreso = anniversary.replace(year=anniversary.year - 1)

        mock_resp = self._mock_equipos_response([
            {"device_id": "T101", "fecha_ingreso": fecha_ingreso.isoformat()}
        ])

        with patch("app.services.incidencia_service.httpx.get", return_value=mock_resp):
            first = incidencia_service.check_annual_calibrations(
                db_session, "http://iot-service:8001"
            )
            second = incidencia_service.check_annual_calibrations(
                db_session, "http://iot-service:8001"
            )

        assert len(first) == 1
        assert len(second) == 0

    def test_check_annual_handles_iot_failure(self, db_session):
        """When iot-service is unavailable, return empty list."""
        with patch(
            "app.services.incidencia_service.httpx.get",
            side_effect=Exception("Connection refused"),
        ):
            created = incidencia_service.check_annual_calibrations(
                db_session, "http://iot-service:8001"
            )

        assert len(created) == 0
