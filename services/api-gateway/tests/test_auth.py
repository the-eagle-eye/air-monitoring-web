from unittest.mock import AsyncMock, patch, MagicMock
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from app.auth.password import verify_password, hash_password


@pytest.fixture
def client():
    return TestClient(app)


# ---- JWT handler tests ----


def test_create_and_verify_access_token():
    data = {"sub": "admin@oefa.gob.pe", "user_id": 1, "rol": "administrador"}
    token = create_access_token(data)
    payload = verify_token(token, expected_type="access")
    assert payload is not None
    assert payload["sub"] == "admin@oefa.gob.pe"
    assert payload["user_id"] == 1
    assert payload["rol"] == "administrador"
    assert payload["type"] == "access"


def test_create_and_verify_refresh_token():
    data = {"sub": "admin@oefa.gob.pe", "user_id": 1, "rol": "administrador"}
    token = create_refresh_token(data)
    payload = verify_token(token, expected_type="refresh")
    assert payload is not None
    assert payload["sub"] == "admin@oefa.gob.pe"
    assert payload["type"] == "refresh"


def test_access_token_rejected_as_refresh():
    data = {"sub": "test@test.com", "user_id": 1, "rol": "tecnico"}
    token = create_access_token(data)
    assert verify_token(token, expected_type="refresh") is None


def test_refresh_token_rejected_as_access():
    data = {"sub": "test@test.com", "user_id": 1, "rol": "tecnico"}
    token = create_refresh_token(data)
    assert verify_token(token, expected_type="access") is None


def test_invalid_token():
    assert verify_token("invalid.token.value") is None


# ---- Password tests ----


def test_hash_and_verify_password():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


# ---- Login endpoint tests ----


def _mock_ops_response(user_data, status_code=200):
    """Helper to mock httpx call to ops-service."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = user_data
    return mock_resp


@pytest.fixture
def mock_user_data():
    return {
        "id": 1,
        "email": "admin@oefa.gob.pe",
        "nombre": "Carlos",
        "apellido": "Mendoza",
        "rol": "administrador",
        "estado": "activo",
        "password_hash": hash_password("admin123"),
        "created_at": "2026-01-01T00:00:00",
    }


def test_login_success(client, mock_user_data):
    with patch("app.routes.auth.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(
            return_value=_mock_ops_response(mock_user_data)
        )
        mock_client.return_value = mock_instance

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@oefa.gob.pe", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["usuario"]["email"] == "admin@oefa.gob.pe"
        assert data["usuario"]["rol"] == "administrador"


def test_login_wrong_password(client, mock_user_data):
    with patch("app.routes.auth.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(
            return_value=_mock_ops_response(mock_user_data)
        )
        mock_client.return_value = mock_instance

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@oefa.gob.pe", "password": "wrongpass"},
        )
        assert response.status_code == 401


def test_login_user_not_found(client):
    with patch("app.routes.auth.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(
            return_value=_mock_ops_response({}, status_code=404)
        )
        mock_client.return_value = mock_instance

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "noexiste@oefa.gob.pe", "password": "admin123"},
        )
        assert response.status_code == 401


def test_refresh_success(client):
    data = {"sub": "admin@oefa.gob.pe", "user_id": 1, "rol": "administrador"}
    refresh_tok = create_refresh_token(data)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok},
    )
    assert response.status_code == 200
    resp_data = response.json()
    assert "access_token" in resp_data


def test_refresh_with_invalid_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token"},
    )
    assert response.status_code == 401


def test_me_with_valid_token(client, mock_user_data):
    data = {"sub": "admin@oefa.gob.pe", "user_id": 1, "rol": "administrador"}
    token = create_access_token(data)

    with patch("app.routes.auth.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(
            return_value=_mock_ops_response(mock_user_data)
        )
        mock_client.return_value = mock_instance

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        resp_data = response.json()
        assert resp_data["email"] == "admin@oefa.gob.pe"


def test_me_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 403  # HTTPBearer returns 403 when no creds


def test_logout(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
