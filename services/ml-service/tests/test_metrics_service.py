"""Tests C6 — métricas de monitoreo del modelo.
docs/plan-c1-c6-c4-c5.md fase C6.
"""
from datetime import datetime, timedelta, timezone

from app.models.health_state import HealthDeviceState, HealthReading
from app.models.model_metric import ModelMetric
from app.services import metrics_service as ms

NOW = datetime(2025, 8, 2, 12, 0, tzinfo=timezone.utc)


def _reading(db, device_id, ts, and_alert, state="SANO"):
    db.add(HealthReading(
        device_id=device_id, reading_timestamp=ts, recon_error=0.1, theta=0.05,
        if_anomaly=and_alert, and_alert=and_alert,
        severity="EN_RIESGO" if and_alert else None,
        health_state=state, raw_state=state, hours_since_prev=1.0,
        model_version="vigishield-ensemble-v1",
    ))


def _state(db, device_id, theta=0.05):
    db.add(HealthDeviceState(device_id=device_id, health_state="SANO",
                             theta=theta, candidate_count=0))


# --- C6.T1: cómputo de alert_rate por estación -------------------------------

def test_compute_station_metric_alert_rate(db_session):
    # 10 lecturas, 3 anómalas -> alert_rate 0.3
    for i in range(7):
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=i), False)
    for i in range(3):
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=10 + i), True)
    db_session.commit()

    m = ms.compute_station_metric(db_session, "DEV1", NOW - timedelta(hours=24), NOW)
    assert m.total_readings == 10
    assert m.anomaly_readings == 3
    assert abs(m.alert_rate - 0.3) < 1e-9


def test_compute_station_metric_no_readings(db_session):
    m = ms.compute_station_metric(db_session, "EMPTY", NOW - timedelta(hours=24), NOW)
    assert m.total_readings == 0
    assert m.alert_rate == 0.0


# --- C6.T2: ventana ----------------------------------------------------------

def test_metric_respects_window(db_session):
    _reading(db_session, "DEV1", NOW - timedelta(hours=1), True)     # dentro
    _reading(db_session, "DEV1", NOW - timedelta(hours=48), True)    # fuera
    db_session.commit()
    m = ms.compute_station_metric(db_session, "DEV1", NOW - timedelta(hours=24), NOW)
    assert m.total_readings == 1  # solo la de dentro


# --- independencia por estación ----------------------------------------------

def test_compute_and_store_per_station(db_session):
    _state(db_session, "DEV1", theta=0.05)
    _state(db_session, "DEV2", theta=0.9)
    # DEV1: 2 lecturas, 1 anómala; DEV2: 1 lectura, 0 anómalas
    _reading(db_session, "DEV1", NOW - timedelta(hours=1), True)
    _reading(db_session, "DEV1", NOW - timedelta(hours=2), False)
    _reading(db_session, "DEV2", NOW - timedelta(hours=1), False)
    db_session.commit()

    summary = ms.compute_and_store_metrics(db_session, now=NOW)
    by_station = {s["station_id"]: s for s in summary}
    assert by_station["DEV1"]["alert_rate"] == 0.5
    assert by_station["DEV2"]["alert_rate"] == 0.0
    assert by_station["DEV1"]["theta"] == 0.05
    # se persistieron
    assert db_session.query(ModelMetric).count() == 2


def test_get_metrics_filters_by_station(db_session):
    _state(db_session, "DEV1")
    _state(db_session, "DEV2")
    _reading(db_session, "DEV1", NOW - timedelta(hours=1), True)
    db_session.commit()
    ms.compute_and_store_metrics(db_session, now=NOW)

    rows = ms.get_metrics(db_session, station_id="DEV1")
    assert all(r.station_id == "DEV1" for r in rows)
    assert len(rows) >= 1


# --- C6.T3: endpoints --------------------------------------------------------

def test_run_metrics_endpoint(client):
    resp = client.post("/api/v1/health-monitor/run-metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert "computed" in body
    assert "stations" in body


def test_metrics_endpoint_returns_items(client):
    # sin datos: estructura válida y vacía
    resp = client.get("/api/v1/health-monitor/metrics")
    assert resp.status_code == 200
    assert "items" in resp.json()
