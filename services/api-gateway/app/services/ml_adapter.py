"""Adapts ml-service-isolation (v3) responses to the legacy ml-service shape.

During the coexistence window (Stage 2/3), the frontend and existing
consumers still speak the legacy schema:
    { failure_probability, remaining_useful_life_days, risk_level, ... }

v3 emits:
    { anomaly_score, anomaly_detected, ae_error, ae_threshold,
      iso_forest_anomaly, station_code, episode_id, risk_level, ... }

This module rewrites v3 payloads into the legacy shape (with new v3 fields
preserved as extras), so callers can migrate at their own pace.
"""

from __future__ import annotations

import json
from typing import Any


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def adapt_prediction(v3: dict) -> dict:
    """Convert one v3 prediction dict into legacy-compatible shape."""
    if not isinstance(v3, dict):
        return v3
    score = v3.get("anomaly_score")
    # Map unbounded anomaly_score → [0, 1] probability-like number.
    # Uses a soft cap: score of 1.0 (== threshold) → 0.5; higher scores
    # asymptote toward 1.0.
    failure_probability = None
    if score is not None:
        s = float(score)
        failure_probability = _clamp(s / (s + 1.0), 0.0, 1.0)

    adapted = dict(v3)
    adapted["failure_probability"] = failure_probability
    adapted["remaining_useful_life_days"] = None  # v3 does not predict RUL
    return adapted


def adapt_json_bytes(raw: bytes) -> bytes:
    """Adapt a JSON body (bytes) coming back from ml-service-isolation.

    Handles: single object with `anomaly_score`, list of such objects,
    or paginated {items: [...]}. Otherwise returns unchanged.
    """
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return raw

    adapted = _adapt_any(payload)
    return json.dumps(adapted).encode("utf-8")


def _adapt_any(obj: Any) -> Any:
    if isinstance(obj, dict):
        if "anomaly_score" in obj:
            return adapt_prediction(obj)
        if "items" in obj and isinstance(obj["items"], list):
            new = dict(obj)
            new["items"] = [_adapt_any(x) for x in obj["items"]]
            return new
        return obj
    if isinstance(obj, list):
        return [_adapt_any(x) for x in obj]
    return obj
