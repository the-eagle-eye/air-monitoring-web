"""
Generate synthetic lifecycle data for Thermo 450i SO2/H2S analyzers.

Simulates equipment degradation over time to train predictive maintenance models.
Each cycle represents one equipment's full lifecycle from new to failure.
"""

import numpy as np
import pandas as pd

# Baseline ranges for healthy equipment (matches simulate_iot.py)
SENSOR_BASELINES = {
    "so2_ppb": (20.0, 50.0),
    "h2s_ppb": (1.0, 5.0),
    "reaction_temp": (33.0, 37.0),
    "izs_temp": (32.0, 36.0),
    "pmt_temp": (34.0, 38.0),
    "sample_flow": (440.0, 460.0),
    "pressure": (29.0, 30.5),
    "uv_lamp_intensity": (380.0, 420.0),
    "box_temp": (30.0, 36.0),
    "hvps_v": (660.0, 680.0),
    "conv_temp": (34.0, 37.0),
    "ozone_flow": (470.0, 490.0),
}

SENSOR_NAMES = list(SENSOR_BASELINES.keys())


def _generate_one_cycle(
    cycle_id: int,
    n_samples: int,
    rng: np.random.Generator,
    baselines: dict[str, tuple[float, float]] | None = None,
    max_life_days: int | None = None,
) -> pd.DataFrame:
    """Generate one equipment lifecycle with gradual degradation.

    Args:
        cycle_id: Identifier for this lifecycle.
        n_samples: Number of time-series samples to generate.
        rng: NumPy random generator.
        baselines: Optional sensor baselines dict. Defaults to SENSOR_BASELINES.
        max_life_days: If set, caps total_life_days to this value.
    """
    use_baselines = baselines or SENSOR_BASELINES

    if max_life_days:
        low_life = max(10, max_life_days // 3)
        total_life_days = rng.integers(low_life, max_life_days + 1)
    else:
        total_life_days = rng.integers(90, 366)

    # Progress ratio: 0 (new) to 1 (failure)
    progress = np.linspace(0, 1, n_samples)

    data = {"cycle_id": cycle_id, "sample_idx": np.arange(n_samples)}

    for sensor, (low, high) in use_baselines.items():
        baseline = rng.uniform(low, high)
        noise_std = (high - low) * 0.02  # 2% noise

        values = np.full(n_samples, baseline) + rng.normal(0, noise_std, n_samples)

        # Apply degradation patterns based on sensor type
        if sensor == "uv_lamp_intensity":
            # UV lamp degrades linearly, losing up to 40% at end of life
            degradation = baseline * 0.4 * progress
            values -= degradation
        elif sensor in ("reaction_temp", "box_temp", "conv_temp"):
            # Temperatures increase as equipment degrades
            drift = (high - low) * 1.5 * progress
            values += drift
        elif sensor in ("sample_flow", "ozone_flow"):
            # Flows decrease as equipment degrades
            degradation = baseline * 0.25 * progress
            values -= degradation
        elif sensor == "hvps_v":
            # HVPS becomes unstable near end of life
            instability = progress ** 2 * (high - low) * 3
            values += rng.normal(0, 1, n_samples) * instability
        elif sensor in ("so2_ppb", "h2s_ppb"):
            # Measurement drift increases with degradation
            drift = baseline * 0.3 * progress
            values += drift

        # Add random anomalies that increase near failure
        anomaly_prob = 0.01 + 0.15 * progress**2
        anomaly_mask = rng.random(n_samples) < anomaly_prob
        anomaly_magnitude = rng.uniform(0.5, 2.0, n_samples) * (high - low)
        anomaly_sign = rng.choice([-1, 1], n_samples)
        values[anomaly_mask] += (anomaly_magnitude * anomaly_sign)[anomaly_mask]

        data[sensor] = values

    # Labels
    rul_days = total_life_days * (1 - progress)
    data["rul_days"] = np.maximum(0, rul_days).astype(int)
    data["failure_within_30d"] = (rul_days <= 30).astype(int)

    return pd.DataFrame(data)


def generate_synthetic_dataset(
    n_cycles: int = 50,
    seed: int = 42,
    baselines: dict[str, tuple[float, float]] | None = None,
    max_life_days: int | None = None,
) -> pd.DataFrame:
    """Generate synthetic lifecycle dataset for multiple equipment cycles.

    Args:
        n_cycles: Number of equipment lifecycles to simulate.
        seed: Random seed for reproducibility.
        baselines: Optional sensor baselines dict. Defaults to SENSOR_BASELINES.
        max_life_days: If set, caps total_life_days per cycle to this value.

    Returns:
        DataFrame with sensor readings, rul_days, and failure_within_30d labels.
    """
    rng = np.random.default_rng(seed)
    cycles = []

    for i in range(n_cycles):
        # Each cycle has 3000-8000 samples (5-min intervals)
        n_samples = rng.integers(3000, 8001)
        cycle_df = _generate_one_cycle(
            i, n_samples, rng, baselines=baselines, max_life_days=max_life_days
        )
        cycles.append(cycle_df)

    dataset = pd.concat(cycles, ignore_index=True)
    return dataset
