import numpy as np

from app.ml.feature_engineering import get_feature_names
from app.ml.model_interface import ModelManager, classify_risk


def test_classify_risk():
    assert classify_risk(0) == "alta"
    assert classify_risk(25) == "alta"
    assert classify_risk(29) == "alta"
    assert classify_risk(30) == "media"
    assert classify_risk(31) == "media"
    assert classify_risk(50) == "media"
    assert classify_risk(59) == "media"
    assert classify_risk(60) == "baja"
    assert classify_risk(69) == "baja"
    assert classify_risk(70) == "baja"
    assert classify_risk(100) == "baja"
    assert classify_risk(365) == "baja"


def test_model_manager_not_loaded():
    manager = ModelManager()
    assert not manager.is_loaded
    assert manager.model_version == "unknown"


def test_model_manager_predict(tmp_path):
    """Test prediction with real trained artifacts if available."""
    import os
    artifacts_path = "/app/ml_artifacts"
    if not os.path.exists(os.path.join(artifacts_path, "rul_model.pkl")):
        import pytest
        pytest.skip("Model artifacts not available")

    manager = ModelManager()
    manager.load(artifacts_path)
    assert manager.is_loaded

    # Create a feature vector with all expected features
    feature_names = get_feature_names()
    rng = np.random.default_rng(42)
    features = {name: float(rng.uniform(0, 100)) for name in feature_names}

    result = manager.predict(features)
    assert "failure_probability" in result
    assert "remaining_useful_life_days" in result
    assert "risk_level" in result
    assert 0 <= result["failure_probability"] <= 1
    assert result["remaining_useful_life_days"] >= 0
    assert result["risk_level"] in ("alta", "media", "baja")
