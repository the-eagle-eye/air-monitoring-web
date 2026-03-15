"""
Feature engineering for predictive maintenance models.

Transforms raw sensor readings into features using rolling windows,
statistical aggregations, and sensor ratios.
"""

import numpy as np
import pandas as pd

from app.ml.synthetic_data import SENSOR_NAMES

# Rolling window sizes (in number of 5-min samples)
WINDOWS = {
    "1h": 12,
    "6h": 72,
    "24h": 288,
}


def _rolling_trend(series: pd.Series, window: int) -> pd.Series:
    """Calculate rolling linear trend (slope) over a window."""
    def slope(arr):
        n = len(arr)
        if n < 2:
            return 0.0
        x = np.arange(n, dtype=np.float64)
        y = arr.astype(np.float64)
        valid = ~np.isnan(y)
        if valid.sum() < 2:
            return 0.0
        xv, yv = x[valid], y[valid]
        n_v = len(xv)
        sx = xv.sum()
        sy = yv.sum()
        sxy = (xv * yv).sum()
        sxx = (xv * xv).sum()
        denom = n_v * sxx - sx * sx
        if abs(denom) < 1e-12:
            return 0.0
        return (n_v * sxy - sx * sy) / denom

    return series.rolling(window, min_periods=1).apply(slope, raw=True)


def compute_features_for_series(df: pd.DataFrame) -> pd.DataFrame:
    """Compute features for a single equipment time series.

    Args:
        df: DataFrame with columns matching SENSOR_NAMES, ordered by time.

    Returns:
        DataFrame with original + engineered features.
    """
    # Build all feature columns as a dict, then create DataFrame at once
    feature_dict = {}

    for sensor in SENSOR_NAMES:
        col = df[sensor]
        feature_dict[sensor] = col.values

        for window_name, window_size in WINDOWS.items():
            feature_dict[f"{sensor}_mean_{window_name}"] = (
                col.rolling(window_size, min_periods=1).mean().values
            )
            feature_dict[f"{sensor}_std_{window_name}"] = (
                col.rolling(window_size, min_periods=1).std().fillna(0).values
            )
            feature_dict[f"{sensor}_trend_{window_name}"] = (
                _rolling_trend(col, window_size).values
            )

    # Sensor ratios
    reaction = df["reaction_temp"].values
    box = df["box_temp"].values.copy()
    box[box == 0] = np.nan
    feature_dict["ratio_reaction_box_temp"] = np.where(
        np.isnan(box), 1.0, reaction / box
    )

    sample = df["sample_flow"].values
    ozone = df["ozone_flow"].values.copy()
    ozone[ozone == 0] = np.nan
    feature_dict["ratio_sample_ozone_flow"] = np.where(
        np.isnan(ozone), 1.0, sample / ozone
    )

    features = pd.DataFrame(feature_dict)
    features = features.fillna(0)
    return features


def compute_features_for_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Compute features for a multi-cycle dataset grouped by cycle_id."""
    result_frames = []
    for cycle_id, group in df.groupby("cycle_id"):
        feats = compute_features_for_series(group.reset_index(drop=True))
        feats = feats.copy()
        feats["cycle_id"] = cycle_id
        feats["rul_days"] = group["rul_days"].values
        feats["failure_within_30d"] = group["failure_within_30d"].values
        result_frames.append(feats)

    return pd.concat(result_frames, ignore_index=True)


def compute_features_from_readings(readings: list[dict]) -> dict[str, float]:
    """Compute features from a list of IoT reading dicts (for inference).

    Args:
        readings: List of reading dicts with sensor field names,
                  ordered chronologically (oldest first).

    Returns:
        Dict of feature_name -> value for a single prediction.
    """
    if not readings:
        return {}

    df = pd.DataFrame(readings)

    # Ensure sensor columns exist
    for sensor in SENSOR_NAMES:
        if sensor not in df.columns:
            df[sensor] = np.nan

    features_df = compute_features_for_series(df)
    # Return last row as dict (most recent features)
    last_row = features_df.iloc[-1]
    return {k: float(v) if not np.isnan(v) else 0.0 for k, v in last_row.items()}


def get_feature_names() -> list[str]:
    """Return the ordered list of feature names the model expects."""
    base = list(SENSOR_NAMES)
    for window_name in WINDOWS:
        for sensor in SENSOR_NAMES:
            base.append(f"{sensor}_mean_{window_name}")
            base.append(f"{sensor}_std_{window_name}")
            base.append(f"{sensor}_trend_{window_name}")
    base.append("ratio_reaction_box_temp")
    base.append("ratio_sample_ozone_flow")
    return base
