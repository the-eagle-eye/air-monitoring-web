"""Tests para el endpoint /api/v1/dashboard/kpis del api-gateway.

Cubre:
  - Agregación normal (varios servicios responden 200 con datos).
  - Manejo de fallos por servicio (uno cae -> defaults seguros).
  - Bypass de auth (sin token -> 403 vía HTTPBearer).
"""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.jwt_handler import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


def _token(rol: str = "administrador") -> str:
    return create_access_token(
        {"sub": f"{rol}@oefa.gob.pe", "user_id": 1, "rol": rol}
    )


def _mock_resp(payload, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=payload)
    return resp


class _FakeAsyncClient:
    """Doble asíncrono de httpx.AsyncClient que devuelve una respuesta según URL."""

    def __init__(self, url_map: dict, raise_on: set | None = None):
        self._url_map = url_map
        self._raise_on = raise_on or set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, *args, **kwargs):
        for key in self._raise_on:
            if key in url:
                raise RuntimeError("service down")
        for key, resp in self._url_map.items():
            if key in url:
                return resp
        # default: 500 sin json parseable
        return _mock_resp({}, status_code=500)


def _patch_httpx(url_map, raise_on=None):
    """Devuelve un patch decorator sobre httpx.AsyncClient del módulo dashboard."""
    fake = _FakeAsyncClient(url_map, raise_on=raise_on)
    return patch(
        "app.routes.dashboard.httpx.AsyncClient",
        return_value=fake,
    )


# ---------- happy path ----------


def test_kpis_agrega_valores_de_los_tres_servicios(client):
    url_map = {
        "/iot/equipos": _mock_resp([
            {"device_id": "T101", "estado": "activo"},
            {"device_id": "T102", "estado": "activo"},
            {"device_id": "T103", "estado": "inactivo"},
        ]),
        "/incidencias": _mock_resp({
            "items": [
                {"tipo": "correctiva", "estado": "pendiente"},
                {"tipo": "correctiva", "estado": "en_ejecucion"},
                {"tipo": "calibracion", "estado": "pendiente"},
                {"tipo": "correctiva", "estado": "finalizado"},  # no cuenta
                {"tipo": "otro", "estado": "pendiente"},          # tipo no listado
            ]
        }),
        "/calibraciones": _mock_resp({
            "items": [
                {"fecha_calibracion": None},
                {"fecha_calibracion": None},
                {"fecha_calibracion": "2026-01-01"},
            ]
        }),
    }
    with _patch_httpx(url_map):
        r = client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["equipos"] == {"total": 3, "activos": 2}
    # abiertas: correctiva pendiente + correctiva en_ejecucion + calibracion
    # pendiente + otro pendiente = 4 (por_tipo solo cuenta los tipos conocidos).
    assert data["incidencias"]["abiertas"] == 4
    # tipo "otro" no debe ir en por_tipo
    assert data["incidencias"]["por_tipo"] == {
        "correctiva": 2,
        "calibracion": 1,
    }
    assert data["calibraciones"] == {"pendientes": 2, "total": 3}


# ---------- fault tolerance: cada llamada puede fallar independientemente ----------


def test_kpis_cuando_iot_cae(client):
    url_map = {
        "/incidencias": _mock_resp({"items": []}),
        "/calibraciones": _mock_resp({"items": []}),
    }
    with _patch_httpx(url_map, raise_on={"/iot/equipos"}):
        r = client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert r.status_code == 200
    assert r.json()["equipos"] == {"total": 0, "activos": 0}


def test_kpis_cuando_ops_incidencias_devuelve_500(client):
    url_map = {
        "/iot/equipos": _mock_resp([{"device_id": "T1", "estado": "activo"}]),
        "/incidencias": _mock_resp({}, status_code=500),
        "/calibraciones": _mock_resp({"items": [{"fecha_calibracion": None}]}),
    }
    with _patch_httpx(url_map):
        r = client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["equipos"] == {"total": 1, "activos": 1}
    assert data["incidencias"] == {
        "abiertas": 0, "por_tipo": {"correctiva": 0, "calibracion": 0},
    }
    assert data["calibraciones"] == {"pendientes": 1, "total": 1}


def test_kpis_cuando_calibraciones_devuelve_no_dict(client):
    # Si un endpoint devuelve una lista donde esperamos dict, defaults seguros.
    url_map = {
        "/iot/equipos": _mock_resp([]),
        "/incidencias": _mock_resp({"items": []}),
        "/calibraciones": _mock_resp(["not", "a", "dict"]),
    }
    with _patch_httpx(url_map):
        r = client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert r.status_code == 200
    assert r.json()["calibraciones"] == {"pendientes": 0, "total": 0}


def test_kpis_todos_los_servicios_caidos(client):
    with _patch_httpx({}, raise_on={"iot-service", "ops-service"}):
        r = client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["equipos"] == {"total": 0, "activos": 0}
    assert data["incidencias"]["abiertas"] == 0
    assert data["calibraciones"] == {"pendientes": 0, "total": 0}


# ---------- auth ----------


def test_kpis_requires_authentication(client):
    r = client.get("/api/v1/dashboard/kpis")
    # HTTPBearer devuelve 403 cuando no hay credenciales
    assert r.status_code == 403


def test_kpis_rejects_invalid_token(client):
    r = client.get(
        "/api/v1/dashboard/kpis",
        headers={"Authorization": "Bearer not.a.token"},
    )
    assert r.status_code == 401


# ---------- variaciones de forma de respuesta upstream ----------


def test_kpis_ignora_incidencias_no_dict(client):
    # ops devuelve lista en vez de dict con "items" -> defaults seguros
    url_map = {
        "/iot/equipos": _mock_resp([]),
        "/incidencias": _mock_resp([{"tipo": "correctiva", "estado": "pendiente"}]),
        "/calibraciones": _mock_resp({"items": []}),
    }
    with _patch_httpx(url_map):
        r = client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    assert r.status_code == 200
    assert r.json()["incidencias"]["abiertas"] == 0


def test_kpis_incidencias_por_tipo_solo_cuenta_abiertas(client):
    # una correctiva pendiente + una correctiva finalizada -> solo la primera cuenta
    url_map = {
        "/iot/equipos": _mock_resp([]),
        "/incidencias": _mock_resp({
            "items": [
                {"tipo": "correctiva", "estado": "pendiente"},
                {"tipo": "correctiva", "estado": "finalizado"},
                {"tipo": "calibracion", "estado": "cancelado"},
            ]
        }),
        "/calibraciones": _mock_resp({"items": []}),
    }
    with _patch_httpx(url_map):
        r = client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    data = r.json()
    assert data["incidencias"]["abiertas"] == 1
    assert data["incidencias"]["por_tipo"] == {"correctiva": 1, "calibracion": 0}
