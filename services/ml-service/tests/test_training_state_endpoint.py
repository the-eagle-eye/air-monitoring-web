"""Fase 7 — Endpoint GET /health-monitor/training-state.

Ver docs/spec-auto-training-onboarding.md §8.
"""
from datetime import datetime, timezone

import pytest

from app.models.station_training import StationTrainingState
from app.services import training_service as ts


@pytest.fixture
def small_target(monkeypatch):
    """Umbral pequeño para probar `target` y eta_days sin generar 2016 filas."""
    monkeypatch.setattr(ts, "WARMUP_MIN_ROWS", 100)


class TestTrainingStateEndpoint:
    def test_lists_only_non_trained_by_default(
        self, client, db_session, small_target
    ):
        db_session.add_all([
            StationTrainingState(
                device_id="CA-TA-01", state="recolectando",
                readings_valid_count=50,
            ),
            StationTrainingState(
                device_id="CA-CH-04", state="entrenado",
                readings_valid_count=0,
                model_version="vigishield-ensemble-v1-CA-CH-04-seed",
            ),
        ])
        db_session.commit()

        resp = client.get("/api/v1/health-monitor/training-state")
        assert resp.status_code == 200
        data = resp.json()
        device_ids = [it["device_id"] for it in data["items"]]
        assert device_ids == ["CA-TA-01"]

    def test_lists_all_when_all_query_true(
        self, client, db_session, small_target
    ):
        db_session.add_all([
            StationTrainingState(device_id="CA-TA-01", state="recolectando"),
            StationTrainingState(device_id="CA-CH-04", state="entrenado"),
        ])
        db_session.commit()

        resp = client.get("/api/v1/health-monitor/training-state?all=true")
        assert resp.status_code == 200
        device_ids = sorted(it["device_id"] for it in resp.json()["items"])
        assert device_ids == ["CA-CH-04", "CA-TA-01"]

    def test_eta_days_calculated_only_for_recolectando(
        self, client, db_session, small_target
    ):
        db_session.add_all([
            StationTrainingState(
                device_id="CA-TA-01", state="recolectando",
                readings_valid_count=68,  # 32 rows away → 32*5/1440 = 0.111d
            ),
            StationTrainingState(
                device_id="CA-NEW-01", state="nueva",
                readings_valid_count=0,
            ),
            StationTrainingState(
                device_id="CA-BUSY-01", state="entrenando",
                readings_valid_count=100,
                training_started_at=datetime(2026, 7, 16, tzinfo=timezone.utc),
            ),
        ])
        db_session.commit()

        resp = client.get("/api/v1/health-monitor/training-state")
        items = {it["device_id"]: it for it in resp.json()["items"]}

        assert items["CA-TA-01"]["eta_days"] == 0.11
        assert items["CA-TA-01"]["target"] == 100
        # nueva y entrenando no tienen eta
        assert items["CA-NEW-01"]["eta_days"] is None
        assert items["CA-BUSY-01"]["eta_days"] is None

    def test_reports_error_state_and_last_error(
        self, client, db_session, small_target
    ):
        db_session.add(StationTrainingState(
            device_id="CA-FAIL-01",
            state="error",
            attempts=2,
            last_error="CR-04: recon_error mediano 0.5 > 2.0× 0.1",
        ))
        db_session.commit()

        resp = client.get("/api/v1/health-monitor/training-state")
        item = resp.json()["items"][0]

        assert item["state"] == "error"
        assert item["attempts"] == 2
        assert "CR-04" in item["last_error"]
        assert item["eta_days"] is None

    def test_returns_empty_list_when_no_stations(self, client):
        resp = client.get("/api/v1/health-monitor/training-state")
        assert resp.status_code == 200
        assert resp.json() == {"items": []}
