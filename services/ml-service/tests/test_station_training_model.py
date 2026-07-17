from datetime import datetime, timezone

import pytest

from app.models.station_training import (
    SEEDED_STATIONS,
    VALID_STATES,
    StationTrainingState,
)


class TestStationTrainingStateModel:
    def test_default_state_is_nueva_with_zero_counters(self, db_session):
        row = StationTrainingState(device_id="CA-TA-01")
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)

        assert row.state == "nueva"
        assert row.readings_valid_count == 0
        assert row.attempts == 0
        assert row.model_version is None
        assert row.last_error is None
        assert row.training_started_at is None
        assert row.training_completed_at is None
        assert row.updated_at is not None

    def test_can_transition_full_lifecycle(self, db_session):
        row = StationTrainingState(device_id="CA-TA-01")
        db_session.add(row)
        db_session.commit()

        for state in ("recolectando", "entrenando", "entrenado"):
            row.state = state
            db_session.commit()
            db_session.refresh(row)
            assert row.state == state

    def test_error_state_records_diagnostic_fields(self, db_session):
        row = StationTrainingState(
            device_id="CA-TA-01",
            state="error",
            attempts=2,
            last_error="regresión bajo CR-04",
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)

        assert row.state == "error"
        assert row.attempts == 2
        assert row.last_error == "regresión bajo CR-04"

    def test_entrenado_stamps_completion_and_model_version(self, db_session):
        now = datetime.now(timezone.utc)
        row = StationTrainingState(
            device_id="CA-TA-01",
            state="entrenado",
            training_started_at=now,
            training_completed_at=now,
            model_version="vigishield-ensemble-v1-CA-TA-01-20260716T000000Z",
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)

        assert row.training_completed_at is not None
        assert row.model_version.startswith("vigishield-ensemble-v1-CA-TA-01-")

    def test_device_id_is_primary_key(self, db_session):
        db_session.add(StationTrainingState(device_id="CA-TA-01"))
        db_session.commit()

        db_session.add(StationTrainingState(device_id="CA-TA-01"))
        with pytest.raises(Exception):
            db_session.commit()


class TestConstants:
    def test_valid_states_are_the_five_specd(self):
        assert VALID_STATES == (
            "nueva",
            "recolectando",
            "entrenando",
            "entrenado",
            "error",
        )

    def test_seeded_stations_match_five_vigentes(self):
        # Coincide con los 5 theta_*.json existentes en ml_artifacts_ensemble_v1/.
        # Ver spec §CA-15 y docs/spec-racionalizacion-dashboard-e-incidencias.md.
        assert SEEDED_STATIONS == (
            "CA-CC-01",
            "CA-CH-04",
            "CA-CH-05",
            "CA-ILO-01",
            "CA-UCHU-01",
        )
