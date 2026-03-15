import os
import tempfile

import pytest

from app.ml.real_data_loader import (
    COLUMN_MAP,
    SENSOR_COLUMNS,
    extract_baselines,
    filter_by_equipo,
    load_csv,
)

CSV_CONTENT = """_id,equipo,timestamp,SO2_ppb,H2S_ppb,Reaction_Temp,IZS_Temp,PMT_Temp,SampleFlow,Pressure,UVLampIntensity,Box_Temp,HVPS_V,Conv_Temp,Ozone_flow
id1,T101,2025-12-08 07:37:00,-1.48,-1.33,50.03,0,9.38,640,18.41,1931.66,33.73,647.26,314,0
id2,T101,2025-12-08 07:38:00,-1.39,-1.33,50.03,0,9.31,640,18.47,1932.29,33.98,644.43,314,0
id3,T101,2025-12-08 07:39:00,-1.45,-1.33,50.03,0,9.31,640,18.42,1931.22,33.99,645.43,314,0
id4,T102,2025-11-22 00:00:00,27.13,29.16,49.75,6.79,8.5,592.42,17.32,1961.64,34.22,647.19,312,0
id5,T102,2025-11-22 01:00:00,0,29.16,49.75,8.42,8.5,562.45,17.32,1919.71,34.22,647.19,312,0
"""


@pytest.fixture
def csv_path():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        f.write(CSV_CONTENT)
        path = f.name
    yield path
    os.unlink(path)


def test_load_csv(csv_path):
    df = load_csv(csv_path)
    assert len(df) == 5
    assert "equipo" in df.columns
    assert "timestamp" in df.columns
    for sensor in SENSOR_COLUMNS:
        assert sensor in df.columns


def test_load_csv_renames_columns(csv_path):
    df = load_csv(csv_path)
    # Original CSV column names should not be present
    for csv_col in COLUMN_MAP.keys():
        if csv_col not in ("equipo", "timestamp"):
            assert csv_col not in df.columns


def test_load_csv_sorted_by_timestamp(csv_path):
    df = load_csv(csv_path)
    timestamps = df["timestamp"].tolist()
    assert timestamps == sorted(timestamps)


def test_filter_by_equipo(csv_path):
    df = load_csv(csv_path)

    t101 = filter_by_equipo(df, "T101")
    assert len(t101) == 3
    assert all(t101["equipo"] == "T101")

    t102 = filter_by_equipo(df, "T102")
    assert len(t102) == 2
    assert all(t102["equipo"] == "T102")


def test_filter_by_equipo_empty(csv_path):
    df = load_csv(csv_path)
    t999 = filter_by_equipo(df, "T999")
    assert len(t999) == 0


def test_extract_baselines(csv_path):
    df = load_csv(csv_path)
    t101 = filter_by_equipo(df, "T101")
    baselines = extract_baselines(t101)

    assert len(baselines) == len(SENSOR_COLUMNS)
    for sensor, (low, high) in baselines.items():
        assert low <= high, f"{sensor}: low ({low}) > high ({high})"

    # SO2 should be negative for T101
    assert baselines["so2_ppb"][0] < 0

    # UV lamp should be high for T101
    assert baselines["uv_lamp_intensity"][0] > 1900


def test_extract_baselines_zero_sensors(csv_path):
    """Sensors with constant zero should get a minimum range."""
    df = load_csv(csv_path)
    t101 = filter_by_equipo(df, "T101")
    baselines = extract_baselines(t101)

    # izs_temp is 0 for T101, should have minimal range
    low, high = baselines["izs_temp"]
    assert high - low >= 0.5

    # ozone_flow is 0 for T101
    low, high = baselines["ozone_flow"]
    assert high - low >= 0.5
