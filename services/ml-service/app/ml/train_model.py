"""
Training pipeline for predictive maintenance models.

Generates synthetic data, engineers features, trains Random Forest models,
evaluates metrics, and serializes artifacts.

Usage:
    python -m app.ml.train_model [--output-dir PATH] [--n-cycles N]
"""

import argparse
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.ml.feature_engineering import (
    compute_features_for_dataset,
    get_feature_names,
)
from app.ml.synthetic_data import generate_synthetic_dataset

MODEL_VERSION = "1.0.0"


def _generate_multi_profile_data(csv_path: str) -> pd.DataFrame:
    """Generate combined dataset with 3 equipment profiles from CSV baselines."""
    from app.ml.real_data_loader import extract_baselines, filter_by_equipo, load_csv

    print("  Loading CSV and extracting baselines...")
    df = load_csv(csv_path)

    t101_data = filter_by_equipo(df, "T101")
    t102_data = filter_by_equipo(df, "T102")

    baselines_t101 = extract_baselines(t101_data)
    baselines_t102 = extract_baselines(t102_data)

    print(f"  T101 baselines from {len(t101_data)} readings")
    print(f"  T102 baselines from {len(t102_data)} readings")
    print(f"  T103 baselines = T101 baselines (from CSV)")

    # T101 profile: healthy equipment, normal lifecycle
    print("  Generating T101 profile (healthy, 20 cycles)...")
    t101_dataset = generate_synthetic_dataset(
        n_cycles=20, seed=42, baselines=baselines_t101
    )

    # T102 profile: critical equipment, RUL < 30 days
    print("  Generating T102 profile (critical, 15 cycles, max_life_days=30)...")
    t102_dataset = generate_synthetic_dataset(
        n_cycles=15, seed=43, baselines=baselines_t102, max_life_days=30
    )
    # Offset cycle_ids to avoid collision
    t102_dataset["cycle_id"] = t102_dataset["cycle_id"] + 100

    # T103 profile: medium degradation, RUL < 70 days, uses T101 baselines
    print("  Generating T103 profile (medium, 15 cycles, max_life_days=70)...")
    t103_dataset = generate_synthetic_dataset(
        n_cycles=15, seed=44, baselines=baselines_t101, max_life_days=70
    )
    t103_dataset["cycle_id"] = t103_dataset["cycle_id"] + 200

    combined = pd.concat(
        [t101_dataset, t102_dataset, t103_dataset], ignore_index=True
    )
    return combined


def train(
    output_dir: str = "ml_artifacts",
    n_cycles: int = 50,
    csv_path: str | None = None,
    multi_profile: bool = False,
    model_version: str = MODEL_VERSION,
):
    print(f"=== Training Pipeline v{model_version} ===\n")

    # Step 1: Generate data
    if multi_profile and csv_path:
        print("[1/6] Generating multi-profile calibrated data...")
        raw_data = _generate_multi_profile_data(csv_path)
        data_source = "calibrated_multi_profile"
    else:
        print(f"[1/6] Generating synthetic data ({n_cycles} cycles)...")
        raw_data = generate_synthetic_dataset(n_cycles=n_cycles, seed=42)
        data_source = "synthetic"
    print(f"  Total samples: {len(raw_data):,}")

    # Step 2: Feature engineering
    print("[2/6] Computing features...")
    featured_data = compute_features_for_dataset(raw_data)
    feature_names = get_feature_names()
    print(f"  Features: {len(feature_names)}")

    X = featured_data[feature_names].values
    y_rul = featured_data["rul_days"].values
    y_failure = featured_data["failure_within_30d"].values

    # Step 3: Split data
    print("[3/6] Splitting data (60/20/20)...")
    X_train, X_temp, y_rul_train, y_rul_temp, y_fail_train, y_fail_temp = (
        train_test_split(
            X, y_rul, y_failure, test_size=0.4, random_state=42, stratify=y_failure
        )
    )
    X_val, X_test, y_rul_val, y_rul_test, y_fail_val, y_fail_test = train_test_split(
        X_temp, y_rul_temp, y_fail_temp, test_size=0.5, random_state=42,
        stratify=y_fail_temp
    )
    print(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    # Step 4: Scale features
    print("[4/6] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Step 5: Train models
    print("[5/6] Training models...")

    # RF Regressor for RUL
    print("  Training RUL Regressor...")
    rul_model = RandomForestRegressor(
        n_estimators=200, max_depth=20, min_samples_leaf=5, random_state=42, n_jobs=-1
    )
    rul_model.fit(X_train_scaled, y_rul_train)

    # RF Classifier for failure probability
    print("  Training Failure Classifier...")
    failure_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    failure_model.fit(X_train_scaled, y_fail_train)

    # Step 6: Evaluate
    print("[6/6] Evaluating models...\n")

    # RUL Regressor metrics (on test set)
    rul_pred_test = rul_model.predict(X_test_scaled)
    rul_mae = mean_absolute_error(y_rul_test, rul_pred_test)
    rul_rmse = np.sqrt(mean_squared_error(y_rul_test, rul_pred_test))
    rul_r2 = r2_score(y_rul_test, rul_pred_test)
    print(f"  RUL Regressor (test):")
    print(f"    MAE:  {rul_mae:.2f} days")
    print(f"    RMSE: {rul_rmse:.2f} days")
    print(f"    R²:   {rul_r2:.4f}")

    # Failure Classifier metrics (on test set)
    fail_pred_test = failure_model.predict(X_test_scaled)
    fail_proba = failure_model.predict_proba(X_test_scaled)
    # Handle case where predict_proba returns only 1 class
    if fail_proba.shape[1] == 2:
        fail_prob_test = fail_proba[:, 1]
    else:
        # Single class in predictions - use the probability column available
        fail_prob_test = fail_proba[:, 0] if failure_model.classes_[0] == 1 else 1 - fail_proba[:, 0]
    fail_precision = precision_score(y_fail_test, fail_pred_test, zero_division=0)
    fail_recall = recall_score(y_fail_test, fail_pred_test, zero_division=0)
    fail_f1 = f1_score(y_fail_test, fail_pred_test, zero_division=0)
    fail_auc = roc_auc_score(y_fail_test, fail_prob_test)
    print(f"\n  Failure Classifier (test):")
    print(f"    Precision: {fail_precision:.4f}")
    print(f"    Recall:    {fail_recall:.4f}")
    print(f"    F1:        {fail_f1:.4f}")
    print(f"    ROC-AUC:   {fail_auc:.4f}")

    # Save artifacts
    os.makedirs(output_dir, exist_ok=True)

    joblib.dump(rul_model, os.path.join(output_dir, "rul_model.pkl"))
    joblib.dump(failure_model, os.path.join(output_dir, "failure_model.pkl"))
    joblib.dump(scaler, os.path.join(output_dir, "scaler.pkl"))

    with open(os.path.join(output_dir, "feature_names.json"), "w") as f:
        json.dump(feature_names, f, indent=2)

    metadata = {
        "model_version": model_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_source": data_source,
        "n_samples": len(raw_data),
        "n_features": len(feature_names),
        "rul_regressor": {
            "algorithm": "RandomForestRegressor",
            "n_estimators": 200,
            "mae": round(rul_mae, 2),
            "rmse": round(rul_rmse, 2),
            "r2": round(rul_r2, 4),
        },
        "failure_classifier": {
            "algorithm": "RandomForestClassifier",
            "n_estimators": 200,
            "precision": round(fail_precision, 4),
            "recall": round(fail_recall, 4),
            "f1": round(fail_f1, 4),
            "roc_auc": round(fail_auc, 4),
        },
    }
    with open(os.path.join(output_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    if multi_profile:
        metadata["profiles"] = ["T101_healthy", "T102_critical", "T103_medium"]

    print(f"\n  Artifacts saved to {output_dir}/")
    print("  Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ML models")
    parser.add_argument(
        "--output-dir", default="ml_artifacts", help="Output directory for artifacts"
    )
    parser.add_argument(
        "--n-cycles", type=int, default=50, help="Number of synthetic cycles"
    )
    parser.add_argument(
        "--baselines-from-csv", default=None, help="Path to real CSV for baselines"
    )
    parser.add_argument(
        "--multi-profile",
        action="store_true",
        help="Train with multi-profile (T101/T102/T103)",
    )
    parser.add_argument(
        "--model-version", default=MODEL_VERSION, help="Model version string"
    )
    args = parser.parse_args()
    train(
        output_dir=args.output_dir,
        n_cycles=args.n_cycles,
        csv_path=args.baselines_from_csv,
        multi_profile=args.multi_profile,
        model_version=args.model_version,
    )
