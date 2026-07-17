"""Fase 4 — Trigger de auto-training desde evaluate().

Ver docs/spec-auto-training-onboarding.md §4.2 (punto exacto en el flujo).
Los tests silencian el executor (TRAINING_TRIGGER_ENABLED=0) y mockean
training_service.train_station para no ejecutar sklearn en el test path.
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.models.station_training import StationTrainingState
from app.schemas.health import HealthEvaluateRequest
from app.services import health_service as hs
from app.services import training_service as ts


class _FakeAE:
    def predict(self, X):
        return X  # recon_error = 0 → SANO (no crea incidencias)


class _FakeIF:
    def predict(self, X):
        return np.array([1] * len(X))  # no anómalo


class _FakeScaler:
    def transform(self, X):
        return np.asarray(X, dtype=float)


def _inject_bundle(device_id, theta=0.02):
    hs.registry._cache[device_id] = {
        "scaler": _FakeScaler(),
        "ae": _FakeAE(),
        "iforest": _FakeIF(),
        "theta": theta,
    }


def _req(device_id, ts=None, valido=1):
    return HealthEvaluateRequest(
        device_id=device_id,
        timestamp=ts or datetime(2026, 7, 16, tzinfo=timezone.utc),
        so2_ppb=(4.0 if valido else None),
        so2_flow=(0.4 if valido else None),
        so2_internal_temp=(31.0 if valido else None),
        so2_lamp_int=(92.0 if valido else None),
        valido=valido,
    )


@pytest.fixture(autouse=True)
def _clear_registry():
    yield
    hs.registry._cache.clear()


@pytest.fixture
def small_threshold(monkeypatch):
    """Umbral pequeño para que los tests puedan cruzarlo con pocas lecturas."""
    monkeypatch.setattr(ts, "WARMUP_MIN_ROWS", 3)


@pytest.fixture
def trigger_off(monkeypatch):
    """Silencia el executor.submit — sólo verificamos el estado en DB."""
    monkeypatch.setenv("TRAINING_TRIGGER_ENABLED", "0")


class TestStateAccounting:
    def test_first_valid_reading_creates_state_recolectando(
        self, db_session, small_threshold, trigger_off
    ):
        _inject_bundle("CA-TA-01")
        hs.evaluate(db_session, _req("CA-TA-01"))

        row = db_session.get(StationTrainingState, "CA-TA-01")
        assert row is not None
        assert row.state == "recolectando"
        assert row.readings_valid_count == 1

    def test_first_invalid_reading_creates_state_nueva(
        self, db_session, small_threshold, trigger_off
    ):
        """Lectura sin valido=1 crea la fila pero no acumula (spec §4.2 paso 3)."""
        _inject_bundle("CA-TA-01")
        hs.evaluate(db_session, _req("CA-TA-01", valido=0))

        row = db_session.get(StationTrainingState, "CA-TA-01")
        assert row is not None
        assert row.state == "nueva"
        assert row.readings_valid_count == 0

    def test_invalid_reading_does_not_increment_when_already_recolectando(
        self, db_session, small_threshold, trigger_off
    ):
        _inject_bundle("CA-TA-01")
        hs.evaluate(db_session, _req("CA-TA-01"))  # count=1
        hs.evaluate(
            db_session,
            _req(
                "CA-TA-01",
                valido=0,
                ts=datetime(2026, 7, 16, 0, 5, tzinfo=timezone.utc),
            ),
        )

        row = db_session.get(StationTrainingState, "CA-TA-01")
        assert row.readings_valid_count == 1  # no incrementó
        assert row.state == "recolectando"

    def test_multiple_valid_readings_accumulate(
        self, db_session, small_threshold, trigger_off
    ):
        _inject_bundle("CA-TA-01")
        base = datetime(2026, 7, 16, tzinfo=timezone.utc)
        for i in range(2):  # threshold=3, aún no cruza
            hs.evaluate(
                db_session,
                _req("CA-TA-01", ts=base + timedelta(minutes=5 * i)),
            )

        row = db_session.get(StationTrainingState, "CA-TA-01")
        assert row.state == "recolectando"
        assert row.readings_valid_count == 2


class TestThresholdTransition:
    def test_crossing_threshold_transitions_to_entrenando(
        self, db_session, small_threshold, trigger_off
    ):
        _inject_bundle("CA-TA-01")
        base = datetime(2026, 7, 16, tzinfo=timezone.utc)
        for i in range(3):  # threshold=3
            hs.evaluate(
                db_session,
                _req("CA-TA-01", ts=base + timedelta(minutes=5 * i)),
            )

        row = db_session.get(StationTrainingState, "CA-TA-01")
        assert row.state == "entrenando"
        assert row.readings_valid_count == 3
        assert row.training_started_at is not None

    def test_crossing_threshold_submits_to_executor_when_enabled(
        self, db_session, small_threshold, monkeypatch
    ):
        _inject_bundle("CA-TA-01")
        monkeypatch.setenv("TRAINING_TRIGGER_ENABLED", "1")

        submitted: list[tuple[str, str]] = []

        class _FakeExecutor:
            def submit(self, fn, *args, **kwargs):
                submitted.append((fn.__name__, args[0] if args else None))

        monkeypatch.setattr(hs, "_training_executor", _FakeExecutor())

        base = datetime(2026, 7, 16, tzinfo=timezone.utc)
        for i in range(3):
            hs.evaluate(
                db_session,
                _req("CA-TA-01", ts=base + timedelta(minutes=5 * i)),
            )

        assert submitted == [("_run_training_job", "CA-TA-01")]


class TestEntrenadoNoop:
    def test_entrenado_stations_do_not_re_trigger(
        self, db_session, small_threshold, trigger_off
    ):
        """CA-15 del spec: las 5 estaciones vigentes se seedean como 'entrenado'
        y no deben volver a acumular ni disparar entrenamiento."""
        _inject_bundle("CA-CH-04")
        db_session.add(StationTrainingState(
            device_id="CA-CH-04",
            state="entrenado",
            readings_valid_count=0,
            model_version="vigishield-ensemble-v1-CA-CH-04-seed",
        ))
        db_session.commit()

        base = datetime(2026, 7, 16, tzinfo=timezone.utc)
        for i in range(5):
            hs.evaluate(
                db_session,
                _req("CA-CH-04", ts=base + timedelta(minutes=5 * i)),
            )

        row = db_session.get(StationTrainingState, "CA-CH-04")
        assert row.state == "entrenado"
        assert row.readings_valid_count == 0

    def test_entrenando_state_is_noop(
        self, db_session, small_threshold, trigger_off
    ):
        _inject_bundle("CA-TA-01")
        db_session.add(StationTrainingState(
            device_id="CA-TA-01", state="entrenando",
            readings_valid_count=999,
            training_started_at=datetime(2026, 7, 16, tzinfo=timezone.utc),
        ))
        db_session.commit()

        hs.evaluate(db_session, _req("CA-TA-01"))

        row = db_session.get(StationTrainingState, "CA-TA-01")
        assert row.state == "entrenando"
        assert row.readings_valid_count == 999


class TestAntiRace:
    def test_atomic_transition_only_wins_once(self, db_session):
        """La protección real anti-race está en la SQL `UPDATE ... WHERE
        state='recolectando'`: dos workers que ambos vieron el mismo state antes
        de la transición van a competir en la misma UPDATE, y sólo uno recibirá
        rowcount==1. El otro recibirá rowcount==0 y no debe hacer submit."""
        from sqlalchemy import update as sql_update

        db_session.add(StationTrainingState(
            device_id="CA-TA-01",
            state="recolectando",
            readings_valid_count=2,
        ))
        db_session.commit()

        stmt = (
            sql_update(StationTrainingState)
            .where(
                StationTrainingState.device_id == "CA-TA-01",
                StationTrainingState.state == "recolectando",
            )
            .values(
                state="entrenando",
                readings_valid_count=3,
                training_started_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        r1 = db_session.execute(stmt)
        db_session.commit()
        r2 = db_session.execute(stmt)  # mismo WHERE, state ya cambió
        db_session.commit()

        assert r1.rowcount == 1
        assert r2.rowcount == 0

        row = db_session.get(StationTrainingState, "CA-TA-01")
        assert row.state == "entrenando"
        assert row.readings_valid_count == 3

    def test_second_call_after_threshold_does_not_re_submit(
        self, db_session, small_threshold, monkeypatch
    ):
        """Después de cruzar el umbral y entrar en 'entrenando', una nueva
        lectura no debe volver a llamar al executor."""
        _inject_bundle("CA-TA-01")
        monkeypatch.setenv("TRAINING_TRIGGER_ENABLED", "1")

        submissions: list[str] = []

        class _CountingExecutor:
            def submit(self, fn, *args, **kwargs):
                submissions.append(args[0] if args else None)

        monkeypatch.setattr(hs, "_training_executor", _CountingExecutor())

        base = datetime(2026, 7, 16, tzinfo=timezone.utc)
        # threshold=3 → cruza en la 3.ª; la 4.ª ya está en 'entrenando' (no re-submit)
        for i in range(4):
            hs.evaluate(
                db_session,
                _req("CA-TA-01", ts=base + timedelta(minutes=5 * i)),
            )

        assert len(submissions) == 1
