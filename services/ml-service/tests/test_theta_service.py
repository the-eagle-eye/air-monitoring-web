"""Tests C4 — recalibración automática de θ desde la BD.
docs/plan-c1-c6-c4-c5.md fase C4.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.models.health_state import HealthDeviceState, HealthReading
from app.services import theta_service as ts
from app.services.health_service import registry

NOW = datetime(2025, 8, 2, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def art_dir(tmp_path, monkeypatch):
    """Directorio de artefactos temporal con un θ inicial para DEV1."""
    monkeypatch.setattr(registry, "art_dir", str(tmp_path))
    registry._cache.clear()
    theta_file = tmp_path / "theta_DEV1.json"
    theta_file.write_text(json.dumps({
        "station_id": "DEV1", "theta": 0.50, "theta_train": 0.50,
        "theta_source": "train", "theta_percentile": 95,
    }))
    yield tmp_path
    registry._cache.clear()


def _reading(db, device_id, ts_, recon, and_alert):
    db.add(HealthReading(
        device_id=device_id, reading_timestamp=ts_, recon_error=recon,
        theta=0.5, if_anomaly=and_alert, and_alert=and_alert, severity=None,
        health_state="SANO", raw_state="SANO", hours_since_prev=1.0,
        model_version="v1",
    ))


# --- C4.T1: cálculo P95 desde BD ---------------------------------------------

def test_recalibrate_computes_p95(art_dir, db_session, monkeypatch):
    monkeypatch.setattr(ts, "MIN_NORMAL_READINGS", 10)
    # 100 lecturas normales con recon 0.01..1.00 -> P95 ~ 0.95
    for i in range(100):
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=i),
                 recon=(i + 1) / 100.0, and_alert=False)
    db_session.commit()

    r = ts.recalibrate_theta(db_session, "DEV1", now=NOW)
    assert r["action"] == "recalibrated"
    assert 0.9 <= r["theta"] <= 1.0
    # persistido en el JSON
    meta = json.loads((art_dir / "theta_DEV1.json").read_text())
    assert meta["theta"] == pytest.approx(r["theta"])
    assert meta["theta_train"] == 0.50           # conservado
    assert meta["theta_source"] == "recalibrated_db"


# --- C4.T2: guarda por pocas lecturas ----------------------------------------

def test_recalibrate_skips_with_few_readings(art_dir, db_session, monkeypatch):
    monkeypatch.setattr(ts, "MIN_NORMAL_READINGS", 50)
    for i in range(5):  # muy pocas
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=i),
                 recon=0.1, and_alert=False)
    db_session.commit()
    r = ts.recalibrate_theta(db_session, "DEV1", now=NOW)
    assert r["action"] == "skipped"
    # θ NO cambió
    meta = json.loads((art_dir / "theta_DEV1.json").read_text())
    assert meta["theta"] == 0.50


def test_recalibrate_skips_without_model(art_dir, db_session):
    r = ts.recalibrate_theta(db_session, "NOEXISTE", now=NOW)
    assert r["action"] == "skipped"
    assert "sin modelo" in r["reason"]


# --- C4: solo cuenta lecturas normales (no anómalas) -------------------------

def test_recalibrate_excludes_anomalous(art_dir, db_session, monkeypatch):
    monkeypatch.setattr(ts, "MIN_NORMAL_READINGS", 10)
    # 60 normales bajas + 40 anómalas altas: el P95 debe reflejar solo las normales
    for i in range(60):
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=i),
                 recon=0.1, and_alert=False)
    for i in range(40):
        _reading(db_session, "DEV1", NOW - timedelta(hours=2, minutes=i),
                 recon=5.0, and_alert=True)
    db_session.commit()
    r = ts.recalibrate_theta(db_session, "DEV1", now=NOW)
    assert r["theta"] < 1.0  # no contaminado por las anómalas (5.0)


# --- C4.T2b: idempotencia (theta_train se conserva en re-runs) ---------------

def test_recalibrate_idempotent_theta_train(art_dir, db_session, monkeypatch):
    monkeypatch.setattr(ts, "MIN_NORMAL_READINGS", 10)
    for i in range(100):
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=i),
                 recon=(i + 1) / 100.0, and_alert=False)
    db_session.commit()
    ts.recalibrate_theta(db_session, "DEV1", now=NOW)
    ts.recalibrate_theta(db_session, "DEV1", now=NOW)  # segunda vez
    meta = json.loads((art_dir / "theta_DEV1.json").read_text())
    assert meta["theta_train"] == 0.50  # nunca se sobreescribe con el recalibrado


# --- C4.T3: invalidación de cache del registry -------------------------------

def test_recalibrate_invalidates_cache(art_dir, db_session, monkeypatch):
    monkeypatch.setattr(ts, "MIN_NORMAL_READINGS", 10)
    # sembrar el cache con un bundle falso para DEV1
    registry._cache["DEV1"] = {"theta": 0.50, "fake": True}
    for i in range(100):
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=i),
                 recon=(i + 1) / 100.0, and_alert=False)
    db_session.commit()
    ts.recalibrate_theta(db_session, "DEV1", now=NOW)
    assert "DEV1" not in registry._cache  # fue invalidado


def test_registry_invalidate_all():
    registry._cache["A"] = {"x": 1}
    registry._cache["B"] = {"x": 2}
    registry.invalidate()
    assert registry._cache == {}


# --- C4.3: recalibrate_all ---------------------------------------------------

def test_recalibrate_all(art_dir, db_session, monkeypatch):
    monkeypatch.setattr(ts, "MIN_NORMAL_READINGS", 10)
    db_session.add(HealthDeviceState(device_id="DEV1", health_state="SANO",
                                     theta=0.5, candidate_count=0))
    db_session.add(HealthDeviceState(device_id="DEV2", health_state="SANO",
                                     theta=0.5, candidate_count=0))
    for i in range(100):
        _reading(db_session, "DEV1", NOW - timedelta(hours=1, minutes=i),
                 recon=(i + 1) / 100.0, and_alert=False)
    db_session.commit()
    results = ts.recalibrate_all(db_session, now=NOW)
    by = {r["station_id"]: r for r in results}
    assert by["DEV1"]["action"] == "recalibrated"
    assert by["DEV2"]["action"] == "skipped"  # sin modelo y sin lecturas


# --- C4.T4: endpoint ---------------------------------------------------------

def test_recalibrate_endpoint(client):
    resp = client.post("/api/v1/health-monitor/recalibrate-theta")
    assert resp.status_code == 200
    assert "results" in resp.json()
