"""Tests ITIL I2.7/I2.8 — auto-cierre de incidencias en 'resuelto'.
docs/spec-itil-v4-incidencias.md §1.1 (IT-08, IT-09).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.health_state import HealthReading
from app.services import autoclose_service as ac

NOW = datetime(2025, 8, 10, 12, 0, tzinfo=timezone.utc)


def _reading(db, device_id, ts, and_alert):
    db.add(HealthReading(
        device_id=device_id, reading_timestamp=ts, recon_error=0.1, theta=0.05,
        if_anomaly=and_alert, and_alert=and_alert, severity=None,
        health_state="SANO" if not and_alert else "EN_RIESGO",
        raw_state="SANO" if not and_alert else "EN_RIESGO",
        hours_since_prev=1.0, model_version="v1",
    ))


class _OpsMock:
    """Captura GET (lista resueltas) y PUT (transiciones) a ops."""
    def __init__(self, resueltas):
        self.resueltas = resueltas
        self.puts = []

    def get(self, url, params=None, timeout=None):
        cap = self

        class _R:
            status_code = 200
            def raise_for_status(self): return None
            def json(self): return {"items": cap.resueltas}
        return _R()

    def put(self, url, json=None, timeout=None):
        self.puts.append({"url": url, "json": json})

        class _R:
            status_code = 200
            def raise_for_status(self): return None
        return _R()


@pytest.fixture
def ops_mock(monkeypatch):
    def _install(resueltas):
        m = _OpsMock(resueltas)
        monkeypatch.setattr(ac.httpx, "get", m.get)
        monkeypatch.setattr(ac.httpx, "put", m.put)
        return m
    return _install


def _inc(id, device_id, resolved_at=NOW):
    return {"id": id, "device_id": device_id, "origen": "monitor_salud",
            "estado": "resuelto", "fecha_resolucion": resolved_at.isoformat()}


# --- IT-08: N SANO consecutivas -> finalizado --------------------------------

def test_autoclose_finalizes_after_n_sano(db_session, ops_mock, monkeypatch):
    monkeypatch.setattr(ac, "N_CONFIRM", 6)
    m = ops_mock([_inc(1, "DEV1")])
    for i in range(6):
        _reading(db_session, "DEV1", NOW - timedelta(minutes=5 * i), and_alert=False)
    db_session.commit()

    out = ac.run_autoclose(db_session, now=NOW)
    assert 1 in out["finalizadas"]
    assert m.puts[0]["json"]["estado"] == "finalizado"


def test_autoclose_not_enough_sano_stays(db_session, ops_mock, monkeypatch):
    monkeypatch.setattr(ac, "N_CONFIRM", 6)
    ops_mock([_inc(1, "DEV1")])
    for i in range(4):  # solo 4 < 6
        _reading(db_session, "DEV1", NOW - timedelta(minutes=5 * i), and_alert=False)
    db_session.commit()
    out = ac.run_autoclose(db_session, now=NOW)
    assert out["finalizadas"] == []
    assert 1 in out["pendientes"]


def test_autoclose_anomaly_keeps_resuelto(db_session, ops_mock, monkeypatch):
    monkeypatch.setattr(ac, "N_CONFIRM", 6)
    ops_mock([_inc(1, "DEV1")])
    # última lectura anómala -> arreglo no confirmado
    _reading(db_session, "DEV1", NOW - timedelta(minutes=1), and_alert=True)
    for i in range(5):
        _reading(db_session, "DEV1", NOW - timedelta(minutes=5 * (i + 2)),
                 and_alert=False)
    db_session.commit()
    out = ac.run_autoclose(db_session, now=NOW)
    assert out["finalizadas"] == []
    assert 1 in out["pendientes"]


# --- IT-09: timeout sin lecturas -> cancelado --------------------------------

def test_autoclose_timeout_cancels(db_session, ops_mock, monkeypatch):
    monkeypatch.setattr(ac, "RESUELTO_TIMEOUT_H", 48)
    # sin lecturas para DEV1, resuelto hace 50h
    m = ops_mock([_inc(1, "DEV1", resolved_at=NOW - timedelta(hours=50))])
    out = ac.run_autoclose(db_session, now=NOW)
    assert 1 in out["canceladas"]
    assert m.puts[0]["json"]["estado"] == "cancelado"


def test_autoclose_no_readings_within_timeout_stays(db_session, ops_mock, monkeypatch):
    monkeypatch.setattr(ac, "RESUELTO_TIMEOUT_H", 48)
    # sin lecturas pero resuelto hace solo 10h -> aún no timeout
    ops_mock([_inc(1, "DEV1", resolved_at=NOW - timedelta(hours=10))])
    out = ac.run_autoclose(db_session, now=NOW)
    assert out["canceladas"] == []
    assert 1 in out["pendientes"]


def test_autoclose_empty_when_no_resolved(db_session, ops_mock):
    ops_mock([])
    out = ac.run_autoclose(db_session, now=NOW)
    assert out == {"finalizadas": [], "canceladas": [], "pendientes": [],
                   "ran_at": NOW.isoformat()}


# --- endpoint ----------------------------------------------------------------

def test_autoclose_endpoint(client, monkeypatch):
    monkeypatch.setattr(ac.httpx, "get", _OpsMock([]).get)
    resp = client.post("/api/v1/health-monitor/run-autoclose")
    assert resp.status_code == 200
    assert "finalizadas" in resp.json()
