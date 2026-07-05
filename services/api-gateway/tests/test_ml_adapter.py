"""Unit tests for the v3 → legacy ML response adapter."""

import json

from app.services.ml_adapter import (
    adapt_json_bytes,
    adapt_prediction,
)


def _v3_pred(score: float = 1.5, **extras):
    base = {
        "id": 1,
        "device_id": "T103",
        "station_code": "CA-UCHU-01",
        "model_version": "v3.0.0",
        "anomaly_detected": True,
        "anomaly_score": score,
        "ae_error": score,
        "ae_threshold": 1.0,
        "iso_forest_anomaly": False,
        "risk_level": "media",
        "episode_id": 42,
    }
    base.update(extras)
    return base


def test_adapt_prediction_adds_failure_probability():
    v3 = _v3_pred(score=1.0)
    out = adapt_prediction(v3)
    # score = 1 → score / (score + 1) = 0.5
    assert out["failure_probability"] == 0.5


def test_adapt_prediction_saturates_high_score():
    out = adapt_prediction(_v3_pred(score=1000.0))
    assert 0.99 <= out["failure_probability"] <= 1.0


def test_adapt_prediction_sets_rul_null():
    out = adapt_prediction(_v3_pred())
    assert out["remaining_useful_life_days"] is None


def test_adapt_prediction_preserves_v3_fields():
    v3 = _v3_pred()
    out = adapt_prediction(v3)
    for k in [
        "anomaly_score", "anomaly_detected", "ae_error", "ae_threshold",
        "iso_forest_anomaly", "station_code", "episode_id", "risk_level",
    ]:
        assert out[k] == v3[k]


def test_adapt_json_bytes_single_object():
    body = json.dumps(_v3_pred()).encode("utf-8")
    out = json.loads(adapt_json_bytes(body).decode("utf-8"))
    assert "failure_probability" in out
    assert out["remaining_useful_life_days"] is None


def test_adapt_json_bytes_paginated_list():
    body = json.dumps({
        "items": [_v3_pred(score=0.5), _v3_pred(score=2.0)],
        "total": 2, "page": 1, "page_size": 50,
    }).encode("utf-8")
    out = json.loads(adapt_json_bytes(body).decode("utf-8"))
    assert out["total"] == 2
    assert all("failure_probability" in i for i in out["items"])


def test_adapt_json_bytes_ignores_non_v3_payload():
    body = json.dumps({"just": "some", "other": "data"}).encode("utf-8")
    out = json.loads(adapt_json_bytes(body).decode("utf-8"))
    assert out == {"just": "some", "other": "data"}


def test_adapt_json_bytes_returns_input_on_invalid_json():
    body = b"not-json-at-all"
    assert adapt_json_bytes(body) == body


def test_adapt_json_bytes_top_level_list():
    body = json.dumps([_v3_pred(score=0.1), _v3_pred(score=3.0)]).encode("utf-8")
    out = json.loads(adapt_json_bytes(body).decode("utf-8"))
    assert isinstance(out, list) and len(out) == 2
    assert all("failure_probability" in x for x in out)
