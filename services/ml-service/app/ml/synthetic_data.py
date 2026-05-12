"""
Generate synthetic lifecycle data for Thermo 450i SO2/H2S analyzers.

Simulates equipment degradation over time to train predictive maintenance models.
Each cycle represents one equipment's full lifecycle from new to failure.
"""

import numpy as np
import pandas as pd

# Baseline ranges for healthy equipment (real CR310 T101 P5-P95 values)
SENSOR_BASELINES = {
    "so2_ppb": (-2.2, -1.3),
    "h2s_ppb": (-1.4, -0.3),
    "reaction_temp": (49.7, 50.1),
    "izs_temp": (0.0, 0.0),
    "pmt_temp": (8.5, 10.0),
    "sample_flow": (590.0, 640.0),
    "pressure": (17.2, 18.5),
    "uv_lamp_intensity": (1930.0, 1955.0),
    "box_temp": (33.9, 35.3),
    "hvps_v": (643.0, 648.0),
    "conv_temp": (312.0, 314.0),
    "ozone_flow": (0.0, 0.0),
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
            # UV lamp degrades linearly, losing up to 50% at end of life
            degradation = baseline * 0.50 * progress
            values -= degradation
        elif sensor in ("reaction_temp", "box_temp", "conv_temp"):
            # Temperatures increase as equipment degrades
            drift = (high - low) * 2.0 * progress
            values += drift
        elif sensor == "sample_flow":
            # Flow decreases as equipment degrades
            degradation = baseline * 0.35 * progress
            values -= degradation
        elif sensor == "hvps_v":
            # HVPS becomes unstable near end of life
            instability = progress ** 2 * (high - low) * 4
            values += rng.normal(0, 1, n_samples) * instability
        elif sensor in ("so2_ppb", "h2s_ppb"):
            # Measurement drift increases with degradation (positive drift)
            drift = abs(baseline) * 0.45 * progress
            values += drift
        elif sensor == "pmt_temp":
            # PMT overheats near failure
            drift = (high - low) * 1.2 * progress
            values += drift

        # Add random anomalies that increase near failure
        anomaly_prob = 0.02 + 0.20 * progress**2
        anomaly_mask = rng.random(n_samples) < anomaly_prob
        anomaly_magnitude = rng.uniform(1.0, 3.0, n_samples) * (high - low if (high - low) > 0 else 1.5)
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
