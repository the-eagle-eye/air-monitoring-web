"""Generate synthetic degraded readings for T102/T103 and POST to IoT service.

Generates sensor readings at a specific degradation level to produce
expected prediction outcomes:
  - T102 with --degradation high: produces readings that should predict RUL < 30
  - T103 with --degradation medium: produces readings that should predict RUL < 70

Usage:
    python scripts/generate_synthetic_readings.py --equipo T102 --degradation high
    python scripts/generate_synthetic_readings.py --equipo T103 --degradation medium
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import requests

sys.path.insert(0, ".")
from app.ml.real_data_loader import COLUMN_MAP, extract_baselines, filter_by_equipo, load_csv
from app.ml.synthetic_data import SENSOR_BASELINES

IOT_BASE_URL = "http://localhost:8001/api/v1/iot/readings"

# Reverse mapping: snake_case -> CSV column name (for payload)
REVERSE_MAP = {v: k for k, v in COLUMN_MAP.items()}

DEGRADATION_PROFILES = {
    "high": {"progress_range": (0.85, 0.98), "n_readings": 50},
    "medium": {"progress_range": (0.50, 0.70), "n_readings": 50},
    "low": {"progress_range": (0.05, 0.20), "n_readings": 50},
}


def generate_degraded_readings(
    baselines: dict[str, tuple[float, float]],
    progress_range: tuple[float, float],
    n_readings: int,
    seed: int = 100,
) -> list[dict]:
    """Generate sensor readings at a specific degradation level.

    Applies the same degradation patterns as synthetic_data.py but at a fixed
    progress level to simulate equipment in a specific state.
    """
    rng = np.random.default_rng(seed)
    progress_values = np.linspace(progress_range[0], progress_range[1], n_readings)

    readings = []
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5 * n_readings)

    for i, progress in enumerate(progress_values):
        reading = {}
        for sensor, (low, high) in baselines.items():
            baseline = (low + high) / 2
            noise_std = (high - low) * 0.02 if (high - low) > 0 else 0.01

            value = baseline + rng.normal(0, noise_std)

            # Apply degradation patterns (matches synthetic_data.py)
            if sensor == "uv_lamp_intensity":
                value -= baseline * 0.4 * progress
            elif sensor in ("reaction_temp", "box_temp", "conv_temp"):
                value += (high - low) * 1.5 * progress
            elif sensor in ("sample_flow", "ozone_flow"):
                value -= baseline * 0.25 * progress
            elif sensor == "hvps_v":
                instability = progress**2 * (high - low) * 3
                value += rng.normal(0, 1) * instability
            elif sensor in ("so2_ppb", "h2s_ppb"):
                value += baseline * 0.3 * progress

            # Add anomalies near failure
            anomaly_prob = 0.01 + 0.15 * progress**2
            if rng.random() < anomaly_prob:
                anomaly_mag = rng.uniform(0.5, 2.0) * (high - low) if (high - low) > 0 else 1.0
                value += rng.choice([-1, 1]) * anomaly_mag

            reading[sensor] = round(value, 2)

        reading["timestamp"] = (base_time + timedelta(minutes=5 * i)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        readings.append(reading)

    return readings


def post_readings(readings: list[dict], equipo: str, base_url: str):
    """POST readings to IoT service."""
    success = 0
    errors = 0

    for reading in readings:
        payload = {"equipo": equipo}
        for sensor_snake, col_csv in REVERSE_MAP.items():
            if sensor_snake in reading:
                payload[col_csv] = reading[sensor_snake]
        payload["timestamp"] = reading["timestamp"]

        try:
            resp = requests.post(base_url, json=payload, timeout=10)
            if resp.status_code in (200, 201):
                success += 1
            else:
                errors += 1
                print(f"  ERROR {resp.status_code}: {resp.text[:100]}")
        except requests.RequestException as e:
            errors += 1
            print(f"  CONNECTION ERROR: {e}")

    return success, errors


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic degraded readings"
    )
    parser.add_argument("--equipo", required=True, help="Equipment ID (e.g. T102)")
    parser.add_argument(
        "--degradation",
        required=True,
        choices=["high", "medium", "low"],
        help="Degradation level",
    )
    parser.add_argument(
        "--csv",
        default="../../dataset/datalogger_db.cr310_readings.csv",
        help="Path to CSV for baselines",
    )
    parser.add_argument(
        "--baselines-from",
        default=None,
        help="Equipment to extract baselines from (default: T101 for T103, T102 for T102)",
    )
    parser.add_argument(
        "--iot-url", default=IOT_BASE_URL, help="IoT service readings URL"
    )
    parser.add_argument(
        "--n-readings", type=int, default=50, help="Number of readings to generate"
    )
    parser.add_argument("--seed", type=int, default=100, help="Random seed")
    args = parser.parse_args()

    profile = DEGRADATION_PROFILES[args.degradation]

    # Determine baselines source
    baselines_equipo = args.baselines_from
    if not baselines_equipo:
        if args.equipo == "T102":
            baselines_equipo = "T102"
        else:
            baselines_equipo = "T101"

    # Try to load baselines from CSV
    try:
        df = load_csv(args.csv)
        source_df = filter_by_equipo(df, baselines_equipo)
        if len(source_df) == 0:
            print(f"No data for {baselines_equipo} in CSV, using T101")
            source_df = filter_by_equipo(df, "T101")
        baselines = extract_baselines(source_df)
        print(f"Baselines extracted from {baselines_equipo} ({len(source_df)} readings)")
    except Exception as e:
        print(f"Could not load CSV: {e}")
        print("Using default synthetic baselines")
        baselines = {k: v for k, v in SENSOR_BASELINES.items()}

    n_readings = args.n_readings or profile["n_readings"]
    progress_range = profile["progress_range"]

    print(
        f"Generating {n_readings} readings for {args.equipo} "
        f"(degradation={args.degradation}, progress={progress_range})"
    )

    readings = generate_degraded_readings(
        baselines, progress_range, n_readings, seed=args.seed
    )

    print(f"Posting {len(readings)} readings to {args.iot_url}...")
    s, e = post_readings(readings, args.equipo, args.iot_url)
    print(f"Result: {s} OK, {e} errors")


if __name__ == "__main__":
    main()
