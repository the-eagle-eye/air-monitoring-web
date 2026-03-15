import numpy as np
import pandas as pd

from app.ml.feature_engineering import (
    compute_features_for_series,
    compute_features_from_readings,
    get_feature_names,
)
from app.ml.synthetic_data import SENSOR_NAMES


def _make_sample_df(n_rows=50):
    rng = np.random.default_rng(42)
    data = {}
    for sensor in SENSOR_NAMES:
        data[sensor] = rng.uniform(10, 100, n_rows)
    return pd.DataFrame(data)


def test_compute_features_shape():
    df = _make_sample_df(50)
    features = compute_features_for_series(df)
    expected_names = get_feature_names()
    assert len(features.columns) == len(expected_names)
    for name in expected_names:
        assert name in features.columns


def test_compute_features_no_nan():
    df = _make_sample_df(50)
    features = compute_features_for_series(df)
    assert not features.isna().any().any()


def test_compute_features_from_readings():
    readings = []
    rng = np.random.default_rng(42)
    for _ in range(20):
        reading = {sensor: float(rng.uniform(10, 100)) for sensor in SENSOR_NAMES}
        readings.append(reading)

    result = compute_features_from_readings(readings)
    assert isinstance(result, dict)
    assert len(result) == len(get_feature_names())
    for name in get_feature_names():
        assert name in result


def test_compute_features_from_empty_readings():
    result = compute_features_from_readings([])
    assert result == {}


def test_ratios_computed():
    df = _make_sample_df(10)
    features = compute_features_for_series(df)
    assert "ratio_reaction_box_temp" in features.columns
    assert "ratio_sample_ozone_flow" in features.columns
