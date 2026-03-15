from app.ml.synthetic_data import SENSOR_NAMES, SENSOR_BASELINES, generate_synthetic_dataset


def test_generate_dataset_shape():
    df = generate_synthetic_dataset(n_cycles=3, seed=42)
    assert len(df) > 0
    for sensor in SENSOR_NAMES:
        assert sensor in df.columns
    assert "rul_days" in df.columns
    assert "failure_within_30d" in df.columns
    assert "cycle_id" in df.columns


def test_generate_dataset_rul_range():
    df = generate_synthetic_dataset(n_cycles=3, seed=42)
    assert df["rul_days"].min() >= 0
    assert df["rul_days"].max() > 30  # Lifecycles should be > 30 days


def test_generate_dataset_failure_labels():
    df = generate_synthetic_dataset(n_cycles=3, seed=42)
    # failure_within_30d should be binary
    assert set(df["failure_within_30d"].unique()).issubset({0, 1})
    # There should be both classes present
    assert df["failure_within_30d"].sum() > 0
    assert (df["failure_within_30d"] == 0).sum() > 0


def test_generate_dataset_degradation():
    df = generate_synthetic_dataset(n_cycles=1, seed=42)
    cycle = df[df["cycle_id"] == 0]
    # UV lamp should degrade (earlier values > later values on average)
    early = cycle.head(100)["uv_lamp_intensity"].mean()
    late = cycle.tail(100)["uv_lamp_intensity"].mean()
    assert early > late


def test_generate_dataset_custom_baselines():
    """Custom baselines should produce data in the specified ranges."""
    custom = {
        "so2_ppb": (-2.0, -1.0),
        "h2s_ppb": (-1.5, -0.5),
        "reaction_temp": (49.0, 51.0),
        "izs_temp": (0.0, 0.5),
        "pmt_temp": (8.0, 10.5),
        "sample_flow": (590.0, 645.0),
        "pressure": (17.0, 19.0),
        "uv_lamp_intensity": (1920.0, 1955.0),
        "box_temp": (33.5, 35.5),
        "hvps_v": (640.0, 648.0),
        "conv_temp": (312.0, 314.0),
        "ozone_flow": (0.0, 0.5),
    }
    df = generate_synthetic_dataset(n_cycles=2, seed=42, baselines=custom)
    assert len(df) > 0
    for sensor in SENSOR_NAMES:
        assert sensor in df.columns
    # Check that default baselines still work (backward compat)
    df_default = generate_synthetic_dataset(n_cycles=2, seed=42)
    assert len(df_default) > 0


def test_generate_dataset_max_life_days():
    """max_life_days should cap the RUL values."""
    df = generate_synthetic_dataset(n_cycles=5, seed=42, max_life_days=30)
    assert len(df) > 0
    # All RUL values should be <= 30
    assert df["rul_days"].max() <= 30
    # Should still have both failure labels
    assert set(df["failure_within_30d"].unique()).issubset({0, 1})


def test_generate_dataset_max_life_days_medium():
    """Medium lifecycle (70 days) should have RUL capped at 70."""
    df = generate_synthetic_dataset(n_cycles=5, seed=42, max_life_days=70)
    assert df["rul_days"].max() <= 70
    assert df["rul_days"].min() >= 0
