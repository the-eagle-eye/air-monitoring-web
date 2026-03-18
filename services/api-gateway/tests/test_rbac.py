from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.jwt_handler import create_access_token
from app.auth.rbac import is_public_route, check_write_permission


@pytest.fixture
def client():
    return TestClient(app)


def _make_token(rol: str = "tecnico") -> str:
    return create_access_token(
        {"sub": f"{rol}@oefa.gob.pe", "user_id": 1, "rol": rol}
    )


def _mock_upstream(content: bytes = b'{"ok": true}', status_code: int = 200):
    """Mock httpx call for proxy upstream."""
    mock_resp = MagicMock()
    mock_resp.content = content
    mock_resp.status_code = status_code
    mock_resp.headers = {"content-type": "application/json"}
    return mock_resp


# ---- is_public_route tests ----


def test_login_is_public():
    assert is_public_route("/api/v1/auth/login", "POST") is True


def test_health_is_public():
    assert is_public_route("/health", "GET") is True


def test_iot_readings_post_is_public():
    assert is_public_route("/api/v1/iot/readings", "POST") is True


def test_iot_readings_get_not_public():
    assert is_public_route("/api/v1/iot/readings", "GET") is False


def test_equipos_not_public():
    assert is_public_route("/api/v1/equipos", "GET") is False


# ---- check_write_permission tests ----


def test_get_always_allowed():
    assert check_write_permission("/api/v1/usuarios", "GET", "coordinador") is True


def test_admin_can_write_usuarios():
    assert check_write_permission("/api/v1/usuarios", "POST", "administrador") is True


def test_tecnico_cannot_write_usuarios():
    assert check_write_permission("/api/v1/usuarios", "POST", "tecnico") is False


def test_coordinador_cannot_write_usuarios():
    assert check_write_permission("/api/v1/usuarios", "POST", "coordinador") is False


def test_tecnico_can_write_incidencias():
    assert check_write_permission("/api/v1/incidencias", "POST", "tecnico") is True


def test_admin_can_write_incidencias():
    assert check_write_permission("/api/v1/incidencias", "POST", "administrador") is True


def test_coordinador_cannot_write_incidencias():
    assert check_write_permission("/api/v1/incidencias", "POST", "coordinador") is False


# ---- Proxy auth integration tests ----


def test_proxy_rejects_unauthenticated_request(client):
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.request = AsyncMock(return_value=_mock_upstream())
        mock_client.return_value = mock_instance

        response = client.get("/api/v1/iot/equipos")
        assert response.status_code == 401


def test_proxy_allows_authenticated_get(client):
    token = _make_token("tecnico")
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.request = AsyncMock(return_value=_mock_upstream())
        mock_client.return_value = mock_instance

        response = client.get(
            "/api/v1/iot/equipos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


def test_proxy_blocks_coordinador_write_to_usuarios(client):
    token = _make_token("coordinador")
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.request = AsyncMock(return_value=_mock_upstream())
        mock_client.return_value = mock_instance

        response = client.post(
            "/api/v1/usuarios",
            json={"test": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_proxy_allows_admin_write_to_usuarios(client):
    token = _make_token("administrador")
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.request = AsyncMock(return_value=_mock_upstream())
        mock_client.return_value = mock_instance

        response = client.post(
            "/api/v1/usuarios",
            json={"test": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


def test_iot_readings_post_bypasses_auth(client):
    with patch("app.routes.proxy.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.request = AsyncMock(return_value=_mock_upstream())
        mock_client.return_value = mock_instance

        response = client.post(
            "/api/v1/iot/readings",
            json={"device_id": "T101"},
        )
        assert response.status_code == 200
