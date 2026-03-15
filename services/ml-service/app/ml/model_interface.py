"""
Model interface for loading trained models and making predictions.
"""

import json
import os

import joblib
import numpy as np


def classify_risk(rul_days: int) -> str:
    """Classify risk level based on RUL.

    - RUL <= 30 → alta
    - RUL > 30 & < 70 → media
    - RUL >= 70 → baja
    """
    if rul_days <= 30:
        return "alta"
    elif rul_days < 70:
        return "media"
    else:
        return "baja"


class ModelManager:
    """Manages ML model loading and prediction."""

    def __init__(self):
        self.rul_model = None
        self.failure_model = None
        self.scaler = None
        self.feature_names: list[str] = []
        self.metadata: dict = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_version(self) -> str:
        return self.metadata.get("model_version", "unknown")

    def load(self, artifacts_path: str) -> None:
        """Load all model artifacts from disk."""
        self.rul_model = joblib.load(os.path.join(artifacts_path, "rul_model.pkl"))
        self.failure_model = joblib.load(
            os.path.join(artifacts_path, "failure_model.pkl")
        )
        self.scaler = joblib.load(os.path.join(artifacts_path, "scaler.pkl"))

        with open(os.path.join(artifacts_path, "feature_names.json")) as f:
            self.feature_names = json.load(f)

        metadata_path = os.path.join(artifacts_path, "model_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path) as f:
                self.metadata = json.load(f)

        self._loaded = True

    def predict(self, features: dict[str, float]) -> dict:
        """Run prediction given a feature dict.

        Args:
            features: Dict mapping feature names to float values.

        Returns:
            Dict with failure_probability, remaining_useful_life_days, risk_level.
        """
        if not self._loaded:
            raise RuntimeError("Models not loaded. Call load() first.")

        # Build feature vector in correct order
        feature_vector = np.array(
            [features.get(name, 0.0) for name in self.feature_names]
        ).reshape(1, -1)

        # Scale
        feature_vector_scaled = self.scaler.transform(feature_vector)

        # Predict RUL
        rul_pred = self.rul_model.predict(feature_vector_scaled)[0]
        rul_days = max(0, int(round(rul_pred)))

        # Predict failure probability
        failure_prob = self.failure_model.predict_proba(feature_vector_scaled)[0][1]

        return {
            "failure_probability": round(float(failure_prob), 4),
            "remaining_useful_life_days": rul_days,
            "risk_level": classify_risk(rul_days),
        }


# Singleton instance
model_manager = ModelManager()
