"""Fase 3 — training_service tests.

Ver docs/spec-auto-training-onboarding.md §4.3 (warm-up), §4.4 (fire-and-forget),
§5 (retrain con CR-04).
"""
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.models.iot_view import EquipoView, LecturaIoTView
from app.models.station_training import StationTrainingState
from app.services import health_service as hs
from app.services import training_service as ts


def _seed_equipo(db, device_id="CA-TEST-01"):
    equipo = EquipoView(device_id=device_id, estado="activo")
    db.add(equipo)
    db.commit()
    db.refresh(equipo)
    return equipo


def _seed_readings(db, equipo_pk, n, oefa=True, start=None, seed=0):
    """Genera n lecturas espaciadas 5 min. `oefa=True` → dentro del rango físico
    OEFA (valido=1 tras _in_oefa_scale); `oefa=False` → escala Thermo → valido=0."""
    start = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
    rng = np.random.RandomState(seed)
    for i in range(n):
        if oefa:
            sensors = {
                "so2_ppb": float(2.5 + rng.randn() * 0.3),
                "so2_flow": float(0.45 + rng.randn() * 0.02),
                "so2_internal_temp": float(31.0 + rng.randn() * 0.2),
                "so2_lamp_int": float(102.0 + rng.randn() * 0.5),
            }
        else:
            sensors = {
                "so2_ppb": -600.0,
                "so2_flow": 600.0,
                "so2_internal_temp": 50.0,
                "so2_lamp_int": 1940.0,
            }
        db.add(LecturaIoTView(
            device_id=equipo_pk,
            timestamp_lectura=start + timedelta(minutes=5 * i),
            sensors=sensors,
        ))
    db.commit()


@pytest.fixture
def art_dir(tmp_path, monkeypatch):
    """Redirige el ART_DIR global del health_service a tmp para no ensuciar el repo."""
    monkeypatch.setattr(hs, "ART_DIR", str(tmp_path))
    return str(tmp_path)


@pytest.fixture
def small_thresholds(monkeypatch):
    """Baja los umbrales — el default 2016 es lento para tests. La ventana de
    retrain se amplía para que los seeds sintéticos no queden fuera del cutoff."""
    monkeypatch.setattr(ts, "WARMUP_MIN_ROWS", 100)
    monkeypatch.setattr(ts, "WARMUP_MAX_ROWS", 150)
    monkeypatch.setattr(ts, "RETRAIN_MIN_ROWS", 100)
    monkeypatch.setattr(ts, "RETRAIN_WINDOW_DAYS", 3650)


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    yield
    hs.registry._cache.clear()


class TestWarmupHappyPath:
    def test_writes_all_four_artifacts_and_marks_entrenado(
        self, db_session, art_dir, small_thresholds
    ):
        equipo = _seed_equipo(db_session, "CA-TEST-01")
        _seed_readings(db_session, equipo.id, n=120)

        result = ts.train_station(db_session, "CA-TEST-01", source="warmup")

        assert result["action"] == "trained"
        assert result["source"] == "warmup"
        assert result["rows_train"] > 0
        assert result["theta"] > 0
        assert result["model_version"].startswith(
            "vigishield-ensemble-v1-CA-TEST-01-"
        )

        for name in (
            "scaler_CA-TEST-01.pkl",
            "autoencoder_CA-TEST-01.pkl",
            "iforest_CA-TEST-01.pkl",
            "theta_CA-TEST-01.json",
        ):
            assert os.path.exists(os.path.join(art_dir, name)), name

        with open(os.path.join(art_dir, "theta_CA-TEST-01.json")) as f:
            meta = json.load(f)
        assert meta["training_source"] == "warmup"
        assert meta["model_version"] == result["model_version"]
        assert meta["rows_train"] == result["rows_train"]
        assert "trained_at" in meta
        assert "median_hsp" in meta

        row = db_session.get(StationTrainingState, "CA-TEST-01")
        assert row.state == "entrenado"
        assert row.model_version == result["model_version"]
        assert row.training_completed_at is not None
        assert row.last_error is None

    def test_registry_invalidated_after_training(
        self, db_session, art_dir, small_thresholds
    ):
        equipo = _seed_equipo(db_session, "CA-TEST-01")
        _seed_readings(db_session, equipo.id, n=120)
        hs.registry._cache["CA-TEST-01"] = None  # stale None pre-training

        ts.train_station(db_session, "CA-TEST-01", source="warmup")

        # invalidate() removes the key entirely (belt & suspenders for G5)
        assert "CA-TEST-01" not in hs.registry._cache


class TestInsufficientData:
    def test_skips_when_below_min_rows(self, db_session, art_dir, small_thresholds):
        equipo = _seed_equipo(db_session, "CA-TEST-01")
        _seed_readings(db_session, equipo.id, n=50)

        result = ts.train_station(db_session, "CA-TEST-01", source="warmup")

        assert result["action"] == "skipped"
        assert "insufficient" in result["reason"]
        assert result["rows_valid"] == 50
        assert not os.path.exists(
            os.path.join(art_dir, "scaler_CA-TEST-01.pkl")
        )

        row = db_session.get(StationTrainingState, "CA-TEST-01")
        assert row.state == "recolectando"
        assert row.readings_valid_count == 50

    def test_no_readings_at_all(self, db_session, art_dir, small_thresholds):
        _seed_equipo(db_session, "CA-EMPTY-01")

        result = ts.train_station(db_session, "CA-EMPTY-01", source="warmup")

        assert result["action"] == "skipped"
        assert result["reason"] == "no readings"
        row = db_session.get(StationTrainingState, "CA-EMPTY-01")
        assert row.state == "recolectando"
        assert row.readings_valid_count == 0


class TestValidoDerivation:
    def test_thermo_scale_rows_do_not_count_toward_min(
        self, db_session, art_dir, small_thresholds
    ):
        """50 OEFA + 100 Thermo → valid_count=50 < 100 → skip. Verifica que la
        derivación via _in_oefa_scale funciona en el path de training."""
        equipo = _seed_equipo(db_session, "CA-MIX-01")
        _seed_readings(db_session, equipo.id, n=50, oefa=True)
        _seed_readings(
            db_session, equipo.id, n=100, oefa=False,
            start=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        result = ts.train_station(db_session, "CA-MIX-01", source="warmup")

        assert result["action"] == "skipped"
        assert result["rows_valid"] == 50


class TestAtomicityOnFailure:
    def test_no_partial_artifacts_when_dump_fails(
        self, db_session, art_dir, small_thresholds, monkeypatch
    ):
        equipo = _seed_equipo(db_session, "CA-CRASH-01")
        _seed_readings(db_session, equipo.id, n=120)

        # Fallar en la 2.ª llamada a joblib.dump (i.e. autoencoder.pkl.tmp).
        original = ts.joblib.dump
        calls = {"n": 0}

        def flaky(obj, path, *a, **kw):
            calls["n"] += 1
            if calls["n"] == 2:
                raise IOError("simulated failure")
            return original(obj, path, *a, **kw)

        monkeypatch.setattr(ts.joblib, "dump", flaky)

        with pytest.raises(IOError):
            ts.train_station(db_session, "CA-CRASH-01", source="warmup")

        # Ningún archivo activo (sin .tmp) ni tmp huérfano debería quedar.
        for name in (
            "scaler_CA-CRASH-01.pkl",
            "scaler_CA-CRASH-01.pkl.tmp",
            "autoencoder_CA-CRASH-01.pkl",
            "autoencoder_CA-CRASH-01.pkl.tmp",
            "iforest_CA-CRASH-01.pkl",
            "theta_CA-CRASH-01.json",
        ):
            assert not os.path.exists(os.path.join(art_dir, name)), name

        row = db_session.get(StationTrainingState, "CA-CRASH-01")
        assert row.state == "error"
        assert row.attempts == 1
        assert "simulated" in (row.last_error or "").lower()


class TestRetrainCR04:
    def test_rejects_when_new_model_worse_than_baseline(
        self, db_session, art_dir, small_thresholds
    ):
        equipo = _seed_equipo(db_session, "CA-CR04-01")
        _seed_readings(db_session, equipo.id, n=120)

        # Baseline "perfecto" (θ_train diminuto) → cualquier retrain lo supera.
        theta_path = os.path.join(art_dir, "theta_CA-CR04-01.json")
        with open(theta_path, "w") as f:
            json.dump({
                "station_id": "CA-CR04-01",
                "theta": 1e-6,
                "theta_train": 1e-6,
                "model_version": "vigishield-ensemble-v1-CA-CR04-01-baseline",
            }, f)

        result = ts.train_station(db_session, "CA-CR04-01", source="retrain")

        assert result["action"] == "rejected_cr04"
        assert "recon_error mediano" in result["reason"]

        # El theta anterior NO se sobreescribe (rollback preservó los artefactos).
        with open(theta_path) as f:
            still = json.load(f)
        assert still["theta_train"] == 1e-6
        assert still["model_version"] == (
            "vigishield-ensemble-v1-CA-CR04-01-baseline"
        )

        row = db_session.get(StationTrainingState, "CA-CR04-01")
        assert row.state == "error"
        assert "CR-04" in (row.last_error or "")

    def test_accepts_when_no_previous_baseline(
        self, db_session, art_dir, small_thresholds
    ):
        """Primer entrenamiento vía source='retrain' (edge case): sin theta_*.json
        previo, CR-04 no aplica → acepta."""
        equipo = _seed_equipo(db_session, "CA-FIRST-01")
        _seed_readings(db_session, equipo.id, n=120)

        result = ts.train_station(db_session, "CA-FIRST-01", source="retrain")

        assert result["action"] == "trained"
        assert result["source"] == "retrain"


class TestInputValidation:
    def test_rejects_unknown_source(self, db_session):
        with pytest.raises(ValueError, match="source"):
            ts.train_station(db_session, "CA-X", source="unknown")
