"""Validate predictions on real CSV data offline (no services needed).

Loads the CSV, computes features, and runs predictions using the trained model.

Usage:
    python scripts/validate_real_data.py --csv PATH --equipo T101
"""

import argparse
import sys

sys.path.insert(0, ".")

from app.ml.feature_engineering import compute_features_from_readings
from app.ml.model_interface import ModelManager
from app.ml.real_data_loader import SENSOR_COLUMNS, filter_by_equipo, load_csv


def validate(csv_path: str, equipo: str, artifacts_dir: str = "ml_artifacts"):
    print(f"=== Offline Validation: {equipo} ===\n")

    # Load CSV
    df = load_csv(csv_path)
    equipo_df = filter_by_equipo(df, equipo)
    print(f"Loaded {len(equipo_df)} readings for {equipo}")

    if len(equipo_df) == 0:
        print("No data found. Exiting.")
        return

    # Convert to list of dicts for feature engineering
    readings = []
    for _, row in equipo_df.iterrows():
        reading = {}
        for sensor in SENSOR_COLUMNS:
            if sensor in row.index:
                reading[sensor] = float(row[sensor]) if row[sensor] is not None else 0.0
        readings.append(reading)

    print(f"Computing features from {len(readings)} readings...")
    features = compute_features_from_readings(readings)
    if not features:
        print("ERROR: No features computed. Check data format.")
        return

    print(f"Features computed: {len(features)} features")

    # Load model
    print(f"Loading model from {artifacts_dir}/...")
    model = ModelManager()
    model.load(artifacts_dir)

    # Predict
    result = model.predict(features)
    print(f"\n{'='*50}")
    print(f"PREDICTION RESULTS for {equipo}:")
    print(f"{'='*50}")
    print(f"  Failure probability: {result['failure_probability']:.4f}")
    print(f"  Remaining useful life: {result['remaining_useful_life_days']} days")
    print(f"  Risk level: {result['risk_level']}")
    print(f"{'='*50}")

    # Show some raw sensor stats
    print(f"\nSensor summary ({equipo}):")
    for sensor in SENSOR_COLUMNS:
        vals = [r.get(sensor, 0) for r in readings]
        if vals:
            print(f"  {sensor}: min={min(vals):.2f}, max={max(vals):.2f}, mean={sum(vals)/len(vals):.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate predictions on real data")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--equipo", required=True, help="Equipment ID")
    parser.add_argument(
        "--artifacts-dir", default="ml_artifacts", help="Path to model artifacts"
    )
    args = parser.parse_args()
    validate(args.csv, args.equipo, args.artifacts_dir)
