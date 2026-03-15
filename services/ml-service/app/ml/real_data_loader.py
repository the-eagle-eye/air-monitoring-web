"""Load and parse real CR310 CSV data for model calibration.

Reads exported CSV from datalogger_db.cr310_readings, maps column names
to the snake_case sensor names used by the ML pipeline, and extracts
per-equipment baseline ranges for calibrated synthetic data generation.
"""

import pandas as pd

# Mapping from CSV column names to internal sensor names
COLUMN_MAP = {
    "SO2_ppb": "so2_ppb",
    "H2S_ppb": "h2s_ppb",
    "Reaction_Temp": "reaction_temp",
    "IZS_Temp": "izs_temp",
    "PMT_Temp": "pmt_temp",
    "SampleFlow": "sample_flow",
    "Pressure": "pressure",
    "UVLampIntensity": "uv_lamp_intensity",
    "Box_Temp": "box_temp",
    "HVPS_V": "hvps_v",
    "Conv_Temp": "conv_temp",
    "Ozone_flow": "ozone_flow",
}

SENSOR_COLUMNS = list(COLUMN_MAP.values())


def load_csv(csv_path: str) -> pd.DataFrame:
    """Load CR310 CSV and return DataFrame with normalized column names.

    Selects only sensor columns + equipo + timestamp, renames to snake_case.
    """
    df = pd.read_csv(csv_path)

    # Filter rows that have a valid equipo
    df = df[df["equipo"].notna() & (df["equipo"] != "")].copy()

    # Rename sensor columns
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Select relevant columns
    keep_cols = ["equipo", "timestamp"] + [
        c for c in SENSOR_COLUMNS if c in df.columns
    ]
    df = df[keep_cols].copy()

    # Convert sensor columns to numeric
    for col in SENSOR_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Parse timestamp and sort
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def filter_by_equipo(df: pd.DataFrame, equipo: str) -> pd.DataFrame:
    """Filter DataFrame for a specific equipment and sort by timestamp."""
    filtered = df[df["equipo"] == equipo].copy()
    filtered = filtered.sort_values("timestamp").reset_index(drop=True)
    return filtered


def extract_baselines(
    df: pd.DataFrame,
    min_range: float = 0.5,
) -> dict[str, tuple[float, float]]:
    """Extract (low, high) baseline ranges per sensor using percentiles.

    For sensors with near-zero or constant values, uses (0.0, min_range)
    to avoid zero-range issues in synthetic data generation.

    Args:
        df: DataFrame with sensor columns (already filtered by equipo).
        min_range: Minimum range width for constant/zero sensors.

    Returns:
        Dict mapping sensor name to (low, high) tuple.
    """
    baselines = {}
    for sensor in SENSOR_COLUMNS:
        if sensor not in df.columns:
            baselines[sensor] = (0.0, min_range)
            continue

        col = df[sensor].dropna()
        if len(col) == 0:
            baselines[sensor] = (0.0, min_range)
            continue

        low = float(col.quantile(0.05))
        high = float(col.quantile(0.95))

        # If range is too narrow or near zero, use minimum range
        if abs(high - low) < min_range and abs(low) < min_range:
            baselines[sensor] = (0.0, min_range)
        elif abs(high - low) < min_range:
            # Constant but non-zero sensor: add small range around mean
            mean = float(col.mean())
            baselines[sensor] = (mean - min_range / 2, mean + min_range / 2)
        else:
            baselines[sensor] = (low, high)

    return baselines
