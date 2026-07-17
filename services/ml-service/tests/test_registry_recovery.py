"""Fase 2 — Fix G5 (registry re-check disk) + model_version propagation (G7).

Ver docs/spec-auto-training-onboarding.md §6 y §7.
"""
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pytest
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from app.models.health_state import HealthReading
from app.schemas.health import HealthEvaluateRequest
from app.services import health_service as hs


def _write_fake_bundle(art_dir, sid, theta=0.5, model_version=None):
    """Escribe artefactos mínimos entrenables (StandardScaler+MLP+IF) + theta.json
    en `art_dir`. Suficiente para que EnsembleRegistry.get() cargue sin errores."""
    rng = np.random.RandomState(0)
    X = rng.randn(200, 5)
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    ae = MLPRegressor(hidden_layer_sizes=(3,), max_iter=50, random_state=0).fit(
        Xs, Xs
    )
    iforest = IsolationForest(n_estimators=10, random_state=0).fit(Xs)

    joblib.dump(scaler, os.path.join(art_dir, f"scaler_{sid}.pkl"))
    joblib.dump(ae, os.path.join(art_dir, f"autoencoder_{sid}.pkl"))
    joblib.dump(iforest, os.path.join(art_dir, f"iforest_{sid}.pkl"))

    theta_meta = {
        "station_id": sid,
        "theta": theta,
        "theta_train": theta,
        "theta_percentile": 95,
    }
    if model_version is not None:
        theta_meta["model_version"] = model_version
    with open(os.path.join(art_dir, f"theta_{sid}.json"), "w") as f:
        json.dump(theta_meta, f)


class TestRegistryG5Recovery:
    def test_get_none_then_appear_via_disk_recheck(self, tmp_path):
        """Estación sin artefactos → cache None. Luego aparecen los artefactos
        (simula el warm-up trainer) y el próximo get() los detecta sin necesidad
        de llamar invalidate() manualmente."""
        reg = hs.EnsembleRegistry(art_dir=str(tmp_path))

        assert reg.get("CA-NEW") is None
        assert reg._cache.get("CA-NEW") is None

        _write_fake_bundle(str(tmp_path), "CA-NEW", theta=0.42)

        bundle = reg.get("CA-NEW")
        assert bundle is not None
        assert bundle["theta"] == 0.42
        assert bundle["scaler"] is not None

    def test_get_caches_bundle_after_load(self, tmp_path):
        """Segunda llamada devuelve el mismo bundle (no recarga desde disco)."""
        reg = hs.EnsembleRegistry(art_dir=str(tmp_path))
        _write_fake_bundle(str(tmp_path), "CA-NEW", theta=0.5)

        b1 = reg.get("CA-NEW")
        b2 = reg.get("CA-NEW")
        assert b1 is b2  # identidad — cache hit real

    def test_invalidate_still_works(self, tmp_path):
        """El fix G5 no rompe invalidate() explícito (belt & suspenders)."""
        reg = hs.EnsembleRegistry(art_dir=str(tmp_path))
        _write_fake_bundle(str(tmp_path), "CA-NEW")

        reg.get("CA-NEW")
        assert "CA-NEW" in reg._cache
        reg.invalidate("CA-NEW")
        assert "CA-NEW" not in reg._cache


class TestRegistryModelVersion:
    def test_get_loads_model_version_from_theta(self, tmp_path):
        reg = hs.EnsembleRegistry(art_dir=str(tmp_path))
        _write_fake_bundle(
            str(tmp_path),
            "CA-TA-01",
            theta=0.3,
            model_version="vigishield-ensemble-v1-CA-TA-01-20260716T000000Z",
        )

        bundle = reg.get("CA-TA-01")
        assert bundle["model_version"] == (
            "vigishield-ensemble-v1-CA-TA-01-20260716T000000Z"
        )

    def test_get_falls_back_to_constant_when_theta_missing_model_version(
        self, tmp_path
    ):
        """Retrocompat: los theta_*.json de las 5 estaciones existentes no tienen
        `model_version` (spec §7, CA-15). Debe caer al MODEL_VERSION constante."""
        reg = hs.EnsembleRegistry(art_dir=str(tmp_path))
        _write_fake_bundle(str(tmp_path), "CA-OLD", theta=0.2, model_version=None)

        bundle = reg.get("CA-OLD")
        assert bundle["model_version"] == hs.MODEL_VERSION


class TestEvaluateUsesBundleModelVersion:
    """El bundle_factory local inyecta el bundle directamente en el cache del
    registry global (patrón usado en test_health_service.py). Aquí probamos que
    evaluate() lee model_version del bundle en lugar del constant."""

    @pytest.fixture(autouse=True)
    def _clear_registry(self):
        yield
        hs.registry._cache.clear()

    def _inject_bundle(self, device_id, theta=0.02, model_version=None):
        # AE que devuelve error 0 y IF sano -> raw_state=SANO -> pipeline persiste
        # sin crear incidencias (evita side-effects HTTP)
        class _FakeAE:
            def predict(self, X):
                return X

        class _FakeIF:
            def predict(self, X):
                return np.array([1] * len(X))

        class _FakeScaler:
            def transform(self, X):
                return np.asarray(X, dtype=float)

        bundle = {
            "scaler": _FakeScaler(),
            "ae": _FakeAE(),
            "iforest": _FakeIF(),
            "theta": theta,
        }
        if model_version is not None:
            bundle["model_version"] = model_version
        hs.registry._cache[device_id] = bundle

    def _req(self, device_id):
        return HealthEvaluateRequest(
            device_id=device_id,
            timestamp=datetime(2026, 7, 16, tzinfo=timezone.utc),
            so2_ppb=4.0,
            so2_flow=0.4,
            so2_internal_temp=31.0,
            so2_lamp_int=92.0,
            valido=1,
        )

    def test_evaluate_persists_bundle_model_version(self, db_session):
        self._inject_bundle(
            "CA-TA-01", model_version="vigishield-ensemble-v1-CA-TA-01-x"
        )
        result = hs.evaluate(db_session, self._req("CA-TA-01"))

        assert result["model_version"] == "vigishield-ensemble-v1-CA-TA-01-x"
        row = (
            db_session.query(HealthReading)
            .filter_by(device_id="CA-TA-01")
            .first()
        )
        assert row.model_version == "vigishield-ensemble-v1-CA-TA-01-x"

    def test_evaluate_falls_back_when_bundle_missing_model_version(
        self, db_session
    ):
        """Bundle sin model_version (theta antiguo, 5 estaciones vigentes) →
        evaluate usa el MODEL_VERSION constant."""
        self._inject_bundle("CA-CH-04", model_version=None)
        result = hs.evaluate(db_session, self._req("CA-CH-04"))

        assert result["model_version"] == hs.MODEL_VERSION
        row = (
            db_session.query(HealthReading)
            .filter_by(device_id="CA-CH-04")
            .first()
        )
        assert row.model_version == hs.MODEL_VERSION

    def test_evaluate_sin_datos_uses_constant(self, db_session):
        """Sin bundle → SIN_DATOS → model_version = constant."""
        req = HealthEvaluateRequest(
            device_id="CA-UNKNOWN",
            timestamp=datetime(2026, 7, 16, tzinfo=timezone.utc),
            so2_ppb=None,
            so2_flow=None,
            so2_internal_temp=None,
            so2_lamp_int=None,
            valido=0,
        )
        result = hs.evaluate(db_session, req)
        assert result["health_state"] == "SIN_DATOS"
        assert result["model_version"] == hs.MODEL_VERSION
