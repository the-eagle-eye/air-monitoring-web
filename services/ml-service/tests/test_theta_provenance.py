"""Fase 6 — Provenance G7 del theta_<sid>.json.

Ver docs/spec-auto-training-onboarding.md §7 (model provenance ampliada).

`training_service._write_artifacts_atomic` escribe: model_version, rows_train,
rows_normal, median_hsp, trained_at, training_source, theta_percentile.

`theta_service.recalibrate_theta` debe PRESERVAR esos campos al recalibrar θ
(usa `meta.update(...)`, spread + set — verificado aquí).
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.models.health_state import HealthReading
from app.services import theta_service
from app.services.health_service import registry


@pytest.fixture
def art_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "art_dir", str(tmp_path))
    registry._cache.clear()
    yield tmp_path
    registry._cache.clear()


class TestRecalibratePreservesProvenance:
    def test_recalibrate_preserves_model_version_and_training_metadata(
        self, art_dir, db_session, monkeypatch
    ):
        """El theta_*.json escrito por el trainer contiene metadata rica; la
        recalibración de θ (C4) sólo debe cambiar el θ activo y añadir campos
        de auditoría de recalibración, SIN borrar la provenance de entrenamiento."""
        monkeypatch.setattr(theta_service, "MIN_NORMAL_READINGS", 5)

        original = {
            "station_id": "DEV1",
            "theta": 0.10,
            "theta_train": 0.10,
            "theta_percentile": 95,
            "model_version": "vigishield-ensemble-v1-DEV1-20260716T000000Z",
            "rows_train": 3200,
            "rows_normal": 3200,
            "median_hsp": 0.083,
            "trained_at": "2026-07-16T00:00:00+00:00",
            "training_source": "warmup",
        }
        theta_path = art_dir / "theta_DEV1.json"
        theta_path.write_text(json.dumps(original))

        # Seed lecturas normales (and_alert=False, recon_error!=None) para que
        # recalibrate_theta pueda calcular un P95 nuevo.
        now = datetime(2026, 8, 1, tzinfo=timezone.utc)
        for i in range(10):
            db_session.add(HealthReading(
                device_id="DEV1",
                reading_timestamp=now - timedelta(hours=i),
                recon_error=0.05 + i * 0.001,
                theta=0.10,
                if_anomaly=False,
                and_alert=False,
                severity=None,
                health_state="SANO",
                raw_state="SANO",
                hours_since_prev=0.0,
                model_version=original["model_version"],
            ))
        db_session.commit()

        result = theta_service.recalibrate_theta(db_session, "DEV1", now=now)
        assert result["action"] == "recalibrated"

        with open(theta_path) as f:
            meta = json.load(f)

        # Provenance preservada
        assert meta["model_version"] == original["model_version"]
        assert meta["rows_train"] == 3200
        assert meta["rows_normal"] == 3200
        assert meta["median_hsp"] == 0.083
        assert meta["trained_at"] == original["trained_at"]
        assert meta["training_source"] == "warmup"
        assert meta["theta_train"] == original["theta_train"]

        # Campos de recalibración añadidos
        assert "recalibrated_at" in meta
        assert meta["theta_source"] == "recalibrated_db"
        assert meta["theta"] != original["theta"]  # sí se actualiza

    def test_recalibrate_survives_missing_optional_provenance(
        self, art_dir, db_session, monkeypatch
    ):
        """Retrocompat: theta antiguo sin model_version/rows_train/etc no debe
        romper la recalibración (edge case de las 5 estaciones vigentes)."""
        monkeypatch.setattr(theta_service, "MIN_NORMAL_READINGS", 5)

        minimal = {
            "station_id": "DEV_OLD",
            "theta": 0.08,
            "theta_train": 0.55,
            "theta_source": "recalibrated_warmup",
            "theta_percentile": 95,
        }
        theta_path = art_dir / "theta_DEV_OLD.json"
        theta_path.write_text(json.dumps(minimal))

        now = datetime(2026, 8, 1, tzinfo=timezone.utc)
        for i in range(10):
            db_session.add(HealthReading(
                device_id="DEV_OLD",
                reading_timestamp=now - timedelta(hours=i),
                recon_error=0.03,
                theta=0.08,
                if_anomaly=False,
                and_alert=False,
                severity=None,
                health_state="SANO",
                raw_state="SANO",
                hours_since_prev=0.0,
                model_version="vigishield-ensemble-v1",
            ))
        db_session.commit()

        result = theta_service.recalibrate_theta(db_session, "DEV_OLD", now=now)
        assert result["action"] == "recalibrated"

        with open(theta_path) as f:
            meta = json.load(f)
        assert "model_version" not in meta  # no aparece si no existía antes
        assert meta["theta_train"] == 0.55  # preservado


class TestTrainingWritesFullProvenance:
    """Doble check contractual: los campos de §7 del spec deben estar todos
    presentes en el theta escrito por el trainer. (El test happy-path de Fase 3
    valida algunos; aquí somos exhaustivos.)"""

    def test_theta_file_contains_all_required_provenance_fields(
        self, tmp_path, db_session, monkeypatch
    ):
        from app.models.iot_view import EquipoView, LecturaIoTView
        from app.services import health_service as hs
        from app.services import training_service as ts
        import numpy as np

        monkeypatch.setattr(hs, "ART_DIR", str(tmp_path))
        monkeypatch.setattr(ts, "WARMUP_MIN_ROWS", 100)
        monkeypatch.setattr(ts, "WARMUP_MAX_ROWS", 150)

        equipo = EquipoView(device_id="CA-PROV-01", estado="activo")
        db_session.add(equipo)
        db_session.commit()

        rng = np.random.RandomState(0)
        start = datetime(2026, 7, 1, tzinfo=timezone.utc)
        for i in range(120):
            db_session.add(LecturaIoTView(
                device_id=equipo.id,
                timestamp_lectura=start + timedelta(minutes=5 * i),
                sensors={
                    "so2_ppb": float(2.5 + rng.randn() * 0.3),
                    "so2_flow": float(0.45 + rng.randn() * 0.02),
                    "so2_internal_temp": float(31.0 + rng.randn() * 0.2),
                    "so2_lamp_int": float(102.0 + rng.randn() * 0.5),
                },
            ))
        db_session.commit()

        result = ts.train_station(db_session, "CA-PROV-01", source="warmup")
        assert result["action"] == "trained"

        with open(tmp_path / "theta_CA-PROV-01.json") as f:
            meta = json.load(f)

        required = {
            "station_id", "theta", "theta_train", "theta_source",
            "theta_percentile", "model_version", "rows_train",
            "rows_normal", "median_hsp", "trained_at", "training_source",
        }
        assert required.issubset(meta.keys()), (
            f"missing: {required - meta.keys()}"
        )
        assert meta["training_source"] == "warmup"
        assert meta["model_version"].startswith(
            "vigishield-ensemble-v1-CA-PROV-01-"
        )
