"""Tests de los endpoints del router de salud (app/api/v1/health.py) y
cobertura de get_db() del módulo database.

Los servicios subyacentes ya están cubiertos en tests dedicados; aquí solo
verificamos la pieza HTTP: 200/404, forma de respuesta y wiring con el
servicio.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.database import SessionLocal, get_db
from app.models.health_state import HealthDeviceState, HealthReading


# ---------------- get_db (database.py) ----------------


def test_get_db_yields_and_closes():
    """La función get_db debe ceder una Session y cerrarla al terminar."""
    gen = get_db()
    session = next(gen)
    # es una Session real (mismo factory que SessionLocal)
    assert hasattr(session, "query")
    assert hasattr(session, "close")
    # se cierra al agotar el generador
    with pytest.raises(StopIteration):
        next(gen)


def test_get_db_closes_on_exception():
    """Si el consumidor lanza una excepción, la sesión igual se cierra
    (el ``finally`` de get_db lo garantiza)."""
    gen = get_db()
    session = next(gen)
    # inyectar close para observar que se llamó
    closed = {"v": False}
    orig_close = session.close

    def _observed_close():
        closed["v"] = True
        orig_close()
    session.close = _observed_close

    # simular abort del consumidor
    gen.close()
    assert closed["v"] is True


def test_session_local_factory_returns_session():
    s = SessionLocal()
    try:
        assert hasattr(s, "query")
    finally:
        s.close()


# ---------------- helpers de seed ----------------


def _seed_state(db, device_id, health_state="SANO",
                last_reading_ts=None):
    st = HealthDeviceState(
        device_id=device_id,
        health_state=health_state,
        last_reading_ts=last_reading_ts,
        last_recon_error=0.01,
        theta=0.02,
        hours_since_prev=0.0,
        transmission_state="OK",
        transmission_severity=None,
        candidate_count=0,
    )
    db.add(st)
    db.commit()
    return st


def _seed_reading(db, device_id, ts, recon_error=0.01, theta=0.02,
                  health_state="SANO", and_alert=False, if_anomaly=False,
                  severity=None):
    r = HealthReading(
        device_id=device_id,
        reading_timestamp=ts,
        recon_error=recon_error,
        theta=theta,
        health_state=health_state,
        and_alert=and_alert,
        if_anomaly=if_anomaly,
        severity=severity,
        hours_since_prev=0.0,
        raw_state=health_state,
        model_version="test",
    )
    db.add(r)
    db.commit()
    return r


# ---------------- POST /evaluate ----------------


def test_evaluate_endpoint_llama_al_servicio_y_devuelve_json(client):
    """El endpoint POST /evaluate debe delegar en health_service.evaluate y
    responder con la forma HealthEvaluateResponse (línea 35)."""
    ts = datetime(2025, 7, 1, tzinfo=timezone.utc)
    fake_response = {
        "device_id": "T101",
        "timestamp": ts.isoformat(),
        "recon_error": 0.01,
        "theta": 0.02,
        "if_anomaly": False,
        "and_alert": False,
        "severity": None,
        "health_state": "SANO",
        "hours_since_prev": 0.0,
        "model_version": "v1",
    }
    with patch("app.api.v1.health.evaluate", return_value=fake_response) as ev:
        r = client.post(
            "/api/v1/health-monitor/evaluate",
            json={
                "device_id": "T101",
                "timestamp": ts.isoformat(),
                "so2_ppb": 4.0, "so2_flow": 0.4,
                "so2_internal_temp": 31.0, "so2_lamp_int": 92.0,
                "valido": 1,
            },
        )
    assert r.status_code == 200
    ev.assert_called_once()
    body = r.json()
    assert body["device_id"] == "T101"
    assert body["health_state"] == "SANO"


# ---------------- GET /{device_id}/state ----------------


def test_device_state_endpoint_devuelve_estado_existente(client, db_session):
    _seed_state(db_session, "T200", health_state="OBSERVADO",
                last_reading_ts=datetime(2025, 7, 1, tzinfo=timezone.utc))
    r = client.get("/api/v1/health-monitor/T200/state")
    assert r.status_code == 200
    data = r.json()
    assert data["device_id"] == "T200"
    assert data["health_state"] == "OBSERVADO"


def test_device_state_endpoint_404_cuando_no_existe(client):
    """Cubre líneas 65-69: HTTPException 404 cuando no hay estado."""
    r = client.get("/api/v1/health-monitor/NOEXISTE/state")
    assert r.status_code == 404
    assert "NOEXISTE" in r.json()["detail"]


# ---------------- GET /{device_id}/readings ----------------


def test_readings_endpoint_vacio(client):
    r = client.get("/api/v1/health-monitor/SIN_DATOS/readings")
    assert r.status_code == 200
    assert r.json() == {"device_id": "SIN_DATOS", "points": []}


def test_readings_endpoint_con_datos(client, db_session):
    ts = datetime(2025, 7, 1, tzinfo=timezone.utc)
    _seed_reading(db_session, "T300", ts)
    r = client.get("/api/v1/health-monitor/T300/readings")
    assert r.status_code == 200
    data = r.json()
    assert data["device_id"] == "T300"
    assert len(data["points"]) == 1
    p = data["points"][0]
    assert p["health_state"] == "SANO"


# ---------------- GET /transmission/no-transmission ----------------


def test_no_transmission_endpoint(client, db_session):
    """Cubre líneas 85-86: transmission/no-transmission."""
    ts = datetime(2025, 7, 1, tzinfo=timezone.utc)
    st = HealthDeviceState(
        device_id="T400",
        health_state="SANO",
        last_reading_ts=ts,
        transmission_state="SIN_TRANSMISION",
        transmission_severity="alta",
        candidate_count=0,
    )
    db_session.add(st)
    db_session.commit()

    r = client.get("/api/v1/health-monitor/transmission/no-transmission")
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["device_id"] == "T400" for i in items)


def test_no_transmission_endpoint_vacio(client):
    r = client.get("/api/v1/health-monitor/transmission/no-transmission")
    assert r.status_code == 200
    assert r.json() == {"items": []}


# ---------------- POST /run-watchdog ----------------


def test_run_watchdog_endpoint(client):
    """Cubre línea 103: POST /run-watchdog on-demand."""
    fake_summary = {
        "evaluated": 0, "marked": [], "cleared": [], "silenced": [],
        "ok": 0, "ran_at": "2025-07-01T00:00:00+00:00",
    }
    with patch(
        "app.api.v1.health.watchdog_service.run_watchdog",
        return_value=fake_summary,
    ) as run:
        r = client.post("/api/v1/health-monitor/run-watchdog")
    assert r.status_code == 200
    run.assert_called_once()
    assert r.json()["evaluated"] == 0


# ---------------- otros endpoints presentes en el router ----------------


def test_metrics_endpoint(client):
    with patch(
        "app.api.v1.health.metrics_service.get_metrics", return_value=[]
    ) as gm:
        r = client.get("/api/v1/health-monitor/metrics")
    assert r.status_code == 200
    gm.assert_called_once()
    assert r.json() == {"items": []}


def test_run_metrics_endpoint(client):
    with patch(
        "app.api.v1.health.metrics_service.compute_and_store_metrics",
        return_value=[],
    ):
        r = client.post("/api/v1/health-monitor/run-metrics")
    assert r.status_code == 200
    assert r.json() == {"computed": 0, "stations": []}


def test_recalibrate_theta_endpoint(client):
    with patch(
        "app.api.v1.health.theta_service.recalibrate_all", return_value=[]
    ):
        r = client.post("/api/v1/health-monitor/recalibrate-theta")
    assert r.status_code == 200
    assert r.json() == {"results": []}


def test_should_retrain_endpoint(client):
    with patch(
        "app.api.v1.health.retrain_service.evaluate_all", return_value=[]
    ):
        r = client.get("/api/v1/health-monitor/should-retrain")
    assert r.status_code == 200
    assert r.json() == {"results": []}


def test_run_autoclose_endpoint(client):
    fake = {"finalizadas": [], "canceladas": [], "pendientes": [],
            "ran_at": "2025-07-01T00:00:00+00:00"}
    with patch(
        "app.api.v1.health.autoclose_service.run_autoclose", return_value=fake
    ):
        r = client.post("/api/v1/health-monitor/run-autoclose")
    assert r.status_code == 200
    assert r.json()["ran_at"] == fake["ran_at"]
