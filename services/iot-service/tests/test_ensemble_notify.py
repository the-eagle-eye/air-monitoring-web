"""Tests C1 — ingesta IoT dispara el ensemble de salud.
docs/plan-c1-c6-c4-c5.md fase C1.
"""
from datetime import datetime, timezone

import pytest

from app.services import ensemble_notify_service as ens


# --- C1.T1: mapeo de features -------------------------------------------------

def test_map_features_thermo_keys():
    # nombres de clave Thermo pero valores en escala OEFA -> mapeo + válido
    sensors = {
        "SO2_ppb": 2.5, "SampleFlow": 0.45, "UVLampIntensity": 100.0,
        "Reaction_Temp": 31.0, "Box_Temp": 45.0,  # extra ignorado
    }
    out = ens.map_to_ensemble_features(sensors)
    assert out == {
        "so2_ppb": 2.5, "so2_flow": 0.45, "so2_lamp_int": 100.0,
        "so2_internal_temp": 31.0, "scale_ok": True, "valido": 1,
    }


def test_map_features_snake_case_variant():
    sensors = {
        "so2_ppb": 3.0, "sample_flow": 0.4, "uv_lamp_intensity": 99.0,
        "reaction_temp": 32.0,
    }
    out = ens.map_to_ensemble_features(sensors)
    assert out["valido"] == 1
    assert out["so2_ppb"] == 3.0
    assert out["so2_flow"] == 0.4


def test_map_features_missing_yields_valido_0():
    # falta SampleFlow -> valido=0 (gate §3.0 lo tratará como SIN_DATOS)
    sensors = {"SO2_ppb": 2.5, "UVLampIntensity": 100.0, "Reaction_Temp": 31.0}
    out = ens.map_to_ensemble_features(sensors)
    assert out["so2_flow"] is None
    assert out["valido"] == 0


def test_map_features_non_numeric_yields_valido_0():
    sensors = {
        "SO2_ppb": "no-num", "SampleFlow": 0.45, "UVLampIntensity": 100.0,
        "Reaction_Temp": 31.0,
    }
    out = ens.map_to_ensemble_features(sensors)
    assert out["so2_ppb"] is None
    assert out["valido"] == 0


def test_map_features_string_numbers_coerced():
    sensors = {
        "SO2_ppb": "2.5", "SampleFlow": "0.45", "UVLampIntensity": "100",
        "Reaction_Temp": "31",
    }
    out = ens.map_to_ensemble_features(sensors)
    assert out["valido"] == 1
    assert out["so2_ppb"] == 2.5


def test_map_features_empty():
    out = ens.map_to_ensemble_features({})
    assert out["valido"] == 0
    assert all(out[f] is None for f in
               ("so2_ppb", "so2_flow", "so2_lamp_int", "so2_internal_temp"))


# --- Fix del bug de escala C10 (memory/project_c1_scale_bug.md) --------------
# El mapeo NO convierte unidades, pero VALIDA que la escala sea la de OEFA (con
# la que se entrenó el ensemble). Una lectura fuera de rango (p.ej. Thermo) se
# marca valido=0 -> gate §3.0 -> SIN_DATOS, evitando recon_error absurdo.

def test_scale_thermo_rejected_valido_0():
    """Escala Thermo (flow~600, lamp~1940): valores crudos pero valido=0."""
    sensors = {
        "SO2_ppb": -1.5, "SampleFlow": 600.0, "UVLampIntensity": 1940.0,
        "Reaction_Temp": 45.0,
    }
    out = ens.map_to_ensemble_features(sensors)
    # no se convierte: los valores se leen tal cual
    assert out["so2_flow"] == 600.0
    assert out["so2_lamp_int"] == 1940.0
    # pero la escala incoherente se rechaza (fix C10): valido=0 -> SIN_DATOS
    assert out["scale_ok"] is False
    assert out["valido"] == 0


def test_scale_oefa_accepted_valido_1():
    """Escala OEFA (flow~0.45, lamp~102) — válida para el ensemble."""
    sensors = {
        "SO2_ppb": 2.86, "SampleFlow": 0.387, "UVLampIntensity": 101.28,
        "Reaction_Temp": 31.59,
    }
    out = ens.map_to_ensemble_features(sensors)
    assert out["so2_flow"] == 0.387
    assert out["so2_lamp_int"] == 101.28
    assert out["scale_ok"] is True
    assert out["valido"] == 1


def test_scale_partial_thermo_rejected():
    """Basta que UNA feature esté fuera de escala para rechazar (flow Thermo)."""
    sensors = {
        "SO2_ppb": 2.5, "SampleFlow": 600.0,  # flow fuera de escala
        "UVLampIntensity": 101.0, "Reaction_Temp": 31.0,
    }
    out = ens.map_to_ensemble_features(sensors)
    assert out["valido"] == 0


def test_scale_boundary_flow_just_within():
    """Frontera: flow justo dentro del rango OEFA (10.0) pasa."""
    sensors = {
        "SO2_ppb": 2.5, "SampleFlow": 9.9, "UVLampIntensity": 101.0,
        "Reaction_Temp": 31.0,
    }
    out = ens.map_to_ensemble_features(sensors)
    assert out["valido"] == 1


# --- cobertura por-feature de _in_oefa_scale (cada rango protegido) ----------
# Base OEFA válida; cada caso saca UNA sola feature de rango para verificar que
# cada límite de OEFA_RANGES está realmente activo. Protege contra ediciones
# accidentales de un rango.
_OEFA_BASE = {"so2_ppb": 2.5, "so2_flow": 0.45,
              "so2_internal_temp": 31.0, "so2_lamp_int": 101.0}


@pytest.mark.parametrize("feature,bad_value", [
    ("so2_ppb", 500.0),          # > 100
    ("so2_ppb", -50.0),          # < -5
    ("so2_flow", 600.0),         # > 10 (Thermo)
    ("so2_flow", 0.0),           # < 0.05
    ("so2_internal_temp", 80.0),  # > 60
    ("so2_lamp_int", 1940.0),    # > 300 (Thermo)
    ("so2_lamp_int", 10.0),      # < 30
])
def test_in_oefa_scale_rejects_each_out_of_range(feature, bad_value):
    features = {**_OEFA_BASE, feature: bad_value}
    assert ens._in_oefa_scale(features) is False


def test_in_oefa_scale_accepts_valid_base():
    assert ens._in_oefa_scale(_OEFA_BASE) is True


def test_in_oefa_scale_rejects_none_feature():
    # una feature None (ausente) -> fuera de escala (no se puede validar)
    features = {**_OEFA_BASE, "so2_flow": None}
    assert ens._in_oefa_scale(features) is False


# --- C1.T2: notify fire-and-forget -------------------------------------------

class _CapturePost:
    def __init__(self, raise_exc=False):
        self.calls = []
        self.raise_exc = raise_exc

    def __call__(self, url, json=None, timeout=None):
        self.calls.append({"url": url, "json": json})
        if self.raise_exc:
            raise RuntimeError("ml-service caído")

        class _Resp:
            status_code = 200

            def raise_for_status(self_inner):
                return None
        return _Resp()


def test_notify_sends_mapped_payload(monkeypatch):
    monkeypatch.setenv("ENSEMBLE_NOTIFY_ENABLED", "1")
    cap = _CapturePost()
    monkeypatch.setattr(ens.httpx, "post", cap)

    ts = datetime(2025, 8, 1, 12, 0, tzinfo=timezone.utc)
    ok = ens.notify_ensemble("T101", ts, {
        "SO2_ppb": 2.5, "SampleFlow": 0.45, "UVLampIntensity": 100.0,
        "Reaction_Temp": 31.0,
    })
    assert ok is True
    assert len(cap.calls) == 1
    body = cap.calls[0]["json"]
    assert body["device_id"] == "T101"
    assert body["so2_ppb"] == 2.5
    assert body["valido"] == 1
    assert "health-monitor/evaluate" in cap.calls[0]["url"]


def test_notify_disabled_does_not_call(monkeypatch):
    monkeypatch.setenv("ENSEMBLE_NOTIFY_ENABLED", "0")
    cap = _CapturePost()
    monkeypatch.setattr(ens.httpx, "post", cap)
    ok = ens.notify_ensemble("T101", datetime.now(timezone.utc), {"SO2_ppb": 1})
    assert ok is False
    assert cap.calls == []


def test_notify_swallows_errors(monkeypatch):
    # un fallo de red NO debe propagar (la ingesta no se rompe)
    monkeypatch.setenv("ENSEMBLE_NOTIFY_ENABLED", "1")
    cap = _CapturePost(raise_exc=True)
    monkeypatch.setattr(ens.httpx, "post", cap)
    ok = ens.notify_ensemble("T101", datetime.now(timezone.utc), {
        "SO2_ppb": 2.5, "SampleFlow": 0.45, "UVLampIntensity": 100.0,
        "Reaction_Temp": 31.0,
    })
    assert ok is False  # falló pero no lanzó
    assert len(cap.calls) == 1


def test_notify_naive_timestamp_becomes_utc_iso(monkeypatch):
    monkeypatch.setenv("ENSEMBLE_NOTIFY_ENABLED", "1")
    cap = _CapturePost()
    monkeypatch.setattr(ens.httpx, "post", cap)
    naive = datetime(2025, 8, 1, 12, 0)  # sin tzinfo
    ens.notify_ensemble("T101", naive, {
        "SO2_ppb": 2.5, "SampleFlow": 0.45, "UVLampIntensity": 100.0,
        "Reaction_Temp": 31.0,
    })
    assert cap.calls[0]["json"]["timestamp"].endswith("+00:00")


# --- C1.T3: integración ruta /readings dispara el ensemble -------------------

def test_ingestion_triggers_ensemble(client, monkeypatch):
    """Un POST a /readings con el flag on dispara 1 notificación al ensemble."""
    from tests.conftest import VALID_READING_PAYLOAD
    monkeypatch.setenv("ENSEMBLE_NOTIFY_ENABLED", "1")
    cap = _CapturePost()
    monkeypatch.setattr(ens.httpx, "post", cap)

    resp = client.post("/api/v1/iot/readings", json=VALID_READING_PAYLOAD)
    assert resp.status_code == 200
    # la lectura se guardó Y se disparó el ensemble
    assert len(cap.calls) == 1
    body = cap.calls[0]["json"]
    assert body["device_id"] == "T101"
    assert body["valido"] == 1  # el payload de prueba trae los 4 features SO2


def test_ingestion_survives_ensemble_failure(client, monkeypatch):
    """Si el ensemble falla, la ingesta igual persiste la lectura (fire-and-forget)."""
    from tests.conftest import VALID_READING_PAYLOAD
    monkeypatch.setenv("ENSEMBLE_NOTIFY_ENABLED", "1")
    monkeypatch.setattr(ens.httpx, "post", _CapturePost(raise_exc=True))

    resp = client.post("/api/v1/iot/readings", json=VALID_READING_PAYLOAD)
    assert resp.status_code == 200  # la ingesta NO se rompió
    # y la lectura quedó persistida
    got = client.get("/api/v1/iot/readings/T101")
    assert got.json()["total"] >= 1


def test_ingestion_thermo_scale_sent_as_invalid(client, monkeypatch):
    """Fix C10 E2E: una lectura Thermo por /readings se persiste Y se envía al
    ensemble con valido=0 (no produce recon absurdo)."""
    monkeypatch.setenv("ENSEMBLE_NOTIFY_ENABLED", "1")
    cap = _CapturePost()
    monkeypatch.setattr(ens.httpx, "post", cap)

    thermo_payload = {
        "equipo": "T101", "timestamp": "2025-10-27 18:30:00",
        "SO2_ppb": -1.5, "SampleFlow": 600.0, "UVLampIntensity": 1940.0,
        "Reaction_Temp": 50.0,
    }
    resp = client.post("/api/v1/iot/readings", json=thermo_payload)
    assert resp.status_code == 200          # ingesta OK
    assert len(cap.calls) == 1              # sí se notificó al ensemble
    assert cap.calls[0]["json"]["valido"] == 0  # pero como no-válida (fix C10)
    assert "scale_ok" not in cap.calls[0]["json"]  # campo interno no se envía
