"""Tests C5 — reentrenamiento por degradación.
docs/plan-c1-c6-c4-c5.md fase C5, spec-transmision §2.3.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.models.model_metric import ModelMetric
from app.services import retrain_service as rs
from app.services.health_service import registry

NOW = datetime(2025, 8, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def art_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "art_dir", str(tmp_path))
    registry._cache.clear()
    yield tmp_path
    registry._cache.clear()


def _theta_file(art_dir, sid, theta, theta_train):
    (art_dir / f"theta_{sid}.json").write_text(json.dumps({
        "station_id": sid, "theta": theta, "theta_train": theta_train,
    }))


def _metric(db, sid, ts, alert_rate, total=100):
    db.add(ModelMetric(
        station_id=sid, window_start=ts, window_end=ts + timedelta(hours=24),
        total_readings=total, anomaly_readings=int(total * alert_rate),
        alert_rate=alert_rate, theta=0.5,
    ))


# --- C5.T1: criterio tasa de alerta ------------------------------------------

def test_high_sustained_alert_rate_triggers(art_dir, db_session):
    # 7 ventanas todas con tasa 0.30 (> 3×0.05=0.15) -> dispara
    for d in range(7):
        _metric(db_session, "DEV1", NOW - timedelta(days=d), alert_rate=0.30)
    db_session.commit()
    r = rs.should_retrain(db_session, "DEV1", now=NOW)
    assert r["retrain"] is True
    assert any("tasa de alerta" in reason for reason in r["reasons"])


def test_normal_alert_rate_does_not_trigger(art_dir, db_session):
    for d in range(7):
        _metric(db_session, "DEV1", NOW - timedelta(days=d), alert_rate=0.04)
    db_session.commit()
    r = rs.should_retrain(db_session, "DEV1", now=NOW)
    assert r["retrain"] is False


def test_alert_rate_not_sustained_does_not_trigger(art_dir, db_session):
    # una ventana alta, el resto normales -> NO sostenida -> no dispara
    _metric(db_session, "DEV1", NOW - timedelta(days=1), alert_rate=0.40)
    _metric(db_session, "DEV1", NOW - timedelta(days=2), alert_rate=0.03)
    db_session.commit()
    r = rs.should_retrain(db_session, "DEV1", now=NOW)
    assert r["retrain"] is False


# --- C5.T1b: criterio θ drift ------------------------------------------------

def test_theta_drift_high_triggers(art_dir, db_session):
    _theta_file(art_dir, "DEV1", theta=1.5, theta_train=0.5)  # ratio 3.0 > 2
    r = rs.should_retrain(db_session, "DEV1", now=NOW)
    assert r["retrain"] is True
    assert any("θ drift" in reason for reason in r["reasons"])


def test_theta_drift_low_triggers(art_dir, db_session):
    _theta_file(art_dir, "DEV1", theta=0.1, theta_train=0.5)  # ratio 0.2 < 0.5
    r = rs.should_retrain(db_session, "DEV1", now=NOW)
    assert r["retrain"] is True


def test_theta_within_range_does_not_trigger(art_dir, db_session):
    _theta_file(art_dir, "DEV1", theta=0.6, theta_train=0.5)  # ratio 1.2 ok
    r = rs.should_retrain(db_session, "DEV1", now=NOW)
    assert r["retrain"] is False


# --- combinación / sin datos -------------------------------------------------

def test_no_metrics_no_theta_does_not_trigger(art_dir, db_session):
    r = rs.should_retrain(db_session, "DEV_EMPTY", now=NOW)
    assert r["retrain"] is False
    assert r["reasons"] == []


def test_evaluate_all(art_dir, db_session):
    for d in range(7):
        _metric(db_session, "DEV1", NOW - timedelta(days=d), alert_rate=0.30)
        _metric(db_session, "DEV2", NOW - timedelta(days=d), alert_rate=0.02)
    db_session.commit()
    results = {r["station_id"]: r for r in rs.evaluate_all(db_session, now=NOW)}
    assert results["DEV1"]["retrain"] is True
    assert results["DEV2"]["retrain"] is False


# --- C5.T2/T3: retrain_station opt-in y guarda -------------------------------

def test_retrain_station_skips_when_disabled(art_dir, db_session, monkeypatch):
    monkeypatch.setattr(rs, "RETRAIN_ENABLED", False)
    r = rs.retrain_station(db_session, "DEV1")
    assert r["action"] == "skipped"


def test_retrain_station_delegates_to_training_service(
    art_dir, db_session, monkeypatch
):
    """Con RETRAIN_ENABLED=1, retrain_station delega en training_service.train_station
    con source='retrain'. Aquí mockeamos el trainer para verificar el contrato."""
    monkeypatch.setattr(rs, "RETRAIN_ENABLED", True)

    called: list[tuple[str, str]] = []

    def _fake_train(db, sid, *, source):
        called.append((sid, source))
        return {
            "station_id": sid, "action": "trained", "source": source,
            "rows_train": 3000, "theta": 0.1, "theta_train": 0.1,
            "model_version": f"vigishield-ensemble-v1-{sid}-fake",
        }

    monkeypatch.setattr(rs.training_service, "train_station", _fake_train)

    r = rs.retrain_station(db_session, "DEV1")

    assert called == [("DEV1", "retrain")]
    assert r["action"] == "trained"
    assert r["source"] == "retrain"


def test_retrain_station_propagates_cr04_rejection(
    art_dir, db_session, monkeypatch
):
    """Cuando el trainer rechaza el bundle por CR-04, retrain_station devuelve
    el mismo payload — sin ocultarlo."""
    monkeypatch.setattr(rs, "RETRAIN_ENABLED", True)

    def _fake_reject(db, sid, *, source):
        return {"station_id": sid, "action": "rejected_cr04",
                "reason": "recon_error mediano 0.5 > 2.0× 0.1"}

    monkeypatch.setattr(rs.training_service, "train_station", _fake_reject)

    r = rs.retrain_station(db_session, "DEV1")

    assert r["action"] == "rejected_cr04"
    assert "recon_error" in r["reason"]


# --- C5.T4: endpoint diagnóstico ---------------------------------------------

def test_should_retrain_endpoint(client):
    resp = client.get("/api/v1/health-monitor/should-retrain")
    assert resp.status_code == 200
    assert "results" in resp.json()
