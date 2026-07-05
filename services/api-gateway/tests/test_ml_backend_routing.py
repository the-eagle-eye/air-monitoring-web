"""Feature-flag routing: /predictions and /alerts go to the right ML backend."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt_handler import create_access_token
from app.config import settings
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _token(rol: str = "admin") -> str:
    return create_access_token(
        {"sub": f"{rol}@oefa.gob.pe", "user_id": 1, "rol": rol}
    )


def _mock_upstream(content: bytes = b'{"items":[]}', status_code: int = 200):
    m = MagicMock()
    m.content = content
    m.status_code = status_code
    m.headers = {"content-type": "application/json"}
    return m


def _install_ac(mock_client, capture: list, response):
    inst = AsyncMock()
    inst.__aenter__ = AsyncMock(return_value=inst)
    inst.__aexit__ = AsyncMock(return_value=False)

    async def _capture_request(method, url, **kwargs):
        capture.append(url)
        return response

    inst.request = AsyncMock(side_effect=_capture_request)
    mock_client.return_value = inst


def test_ml_backend_isolation_routes_predictions_to_isolation(client, monkeypatch):
    monkeypatch.setattr(settings, "ML_BACKEND", "isolation")
    captured: list[str] = []
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        _install_ac(mock_client, captured, _mock_upstream())
        resp = client.get(
            "/api/v1/predictions/T103/latest",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert resp.status_code == 200
    assert captured and settings.ML_ISOLATION_SERVICE_URL in captured[0]


def test_ml_backend_isolation_routes_alerts_to_isolation(client, monkeypatch):
    monkeypatch.setattr(settings, "ML_BACKEND", "isolation")
    captured: list[str] = []
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        _install_ac(mock_client, captured, _mock_upstream())
        resp = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert resp.status_code == 200
    assert captured and settings.ML_ISOLATION_SERVICE_URL in captured[0]


def test_iot_route_unaffected_by_ml_backend(client, monkeypatch):
    """Non-ML routes must always go to their fixed upstream."""
    monkeypatch.setattr(settings, "ML_BACKEND", "isolation")
    captured: list[str] = []
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        _install_ac(mock_client, captured, _mock_upstream())
        resp = client.get(
            "/api/v1/iot/equipos",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert resp.status_code == 200
    assert captured and settings.IOT_SERVICE_URL in captured[0]


def test_isolation_backend_adapts_prediction_body(client, monkeypatch):
    monkeypatch.setattr(settings, "ML_BACKEND", "isolation")
    import json
    v3_body = json.dumps({
        "id": 1,
        "device_id": "T103",
        "station_code": "CA-UCHU-01",
        "model_version": "v3.0.0",
        "anomaly_detected": True,
        "anomaly_score": 1.0,
        "ae_error": 1.0,
        "ae_threshold": 1.0,
        "iso_forest_anomaly": False,
        "risk_level": "media",
        "episode_id": 42,
    }).encode("utf-8")

    captured: list[str] = []
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        _install_ac(mock_client, captured, _mock_upstream(v3_body))
        resp = client.get(
            "/api/v1/predictions/T103/latest",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["failure_probability"] == pytest.approx(0.5)
    assert body["remaining_useful_life_days"] is None
    assert body["anomaly_score"] == 1.0
    assert body["station_code"] == "CA-UCHU-01"
