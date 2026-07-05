"""Tests del watchdog de pérdida de transmisión.
docs/spec-transmision-y-reentrenamiento.md §1 — criterios CT-01..CT-05.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.health_state import HealthDeviceState
from app.services import watchdog_service as wd

NOW = datetime(2025, 8, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def patch_iot_ops(monkeypatch):
    """Mockea las dos llamadas cross-service del watchdog. Configurable por test."""
    cfg = {"devices": ["DEV1"], "open_incidencia": {}}

    def _list(iot_url):
        return cfg["devices"]

    def _has_open(ops_url, device_id):
        return cfg["open_incidencia"].get(device_id, False)

    monkeypatch.setattr(wd, "_list_active_devices", _list)
    monkeypatch.setattr(wd, "_has_open_incidencia", _has_open)
    return cfg


def _seed_state(db, device_id, last_reading_ts, transmission_state="OK",
                severity=None):
    st = HealthDeviceState(
        device_id=device_id, health_state="SANO",
        last_reading_ts=last_reading_ts,
        transmission_state=transmission_state,
        transmission_severity=severity,
        candidate_count=0,
    )
    db.add(st)
    db.commit()
    return st


# --- CT-01: >15 min sin lecturas -> SIN_TRANSMISION severidad baja ---
def test_ct01_gap_mayor_15min_marca_baja(db_session, patch_iot_ops):
    _seed_state(db_session, "DEV1", NOW - timedelta(minutes=20))
    out = wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_state == "SIN_TRANSMISION"
    assert st.transmission_severity == "baja"
    assert any(m["device_id"] == "DEV1" for m in out["marked"])


def test_gap_dentro_tolerancia_no_marca(db_session, patch_iot_ops):
    _seed_state(db_session, "DEV1", NOW - timedelta(minutes=10))
    wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_state == "OK"
    assert st.transmission_severity is None


# --- CT-02: escalada por duración media (>1h) y alta (>24h) ---
def test_ct02_escala_media_mayor_1h(db_session, patch_iot_ops):
    _seed_state(db_session, "DEV1", NOW - timedelta(hours=2))
    wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_severity == "media"


def test_ct02_escala_alta_mayor_24h(db_session, patch_iot_ops):
    _seed_state(db_session, "DEV1", NOW - timedelta(hours=30))
    wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_severity == "alta"


# --- CT-04: reanuda transmisión -> se limpia ---
def test_ct04_reanuda_limpia_estado(db_session, patch_iot_ops):
    # estaba marcado, pero last_reading_ts es reciente (reanudó)
    _seed_state(db_session, "DEV1", NOW - timedelta(minutes=5),
                transmission_state="SIN_TRANSMISION", severity="alta")
    out = wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_state == "OK"
    assert st.transmission_severity is None
    assert "DEV1" in out["cleared"]


# --- CT-05: incidencia abierta silencia ---
def test_ct05_incidencia_abierta_silencia(db_session, patch_iot_ops):
    patch_iot_ops["open_incidencia"] = {"DEV1": True}
    _seed_state(db_session, "DEV1", NOW - timedelta(hours=2))
    out = wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_state == "OK"  # silenciado, no marca
    assert "DEV1" in out["silenced"]


def test_ct05_silenciado_limpia_marca_previa(db_session, patch_iot_ops):
    # si estaba marcado y luego entra en mantenimiento, se limpia
    patch_iot_ops["open_incidencia"] = {"DEV1": True}
    _seed_state(db_session, "DEV1", NOW - timedelta(hours=2),
                transmission_state="SIN_TRANSMISION", severity="media")
    wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_state == "OK"


# --- sin last_reading_ts (nunca recibimos dato) -> no evalúa ---
def test_sin_last_reading_no_evalua(db_session, patch_iot_ops):
    _seed_state(db_session, "DEV1", None)
    out = wd.run_watchdog(db_session, now=NOW)
    st = db_session.get(HealthDeviceState, "DEV1")
    assert st.transmission_state == "OK"
    assert not out["marked"]


# --- multi-equipo: cada uno independiente ---
def test_multi_equipo_independiente(db_session, patch_iot_ops):
    patch_iot_ops["devices"] = ["DEV1", "DEV2", "DEV3"]
    _seed_state(db_session, "DEV1", NOW - timedelta(minutes=5))    # OK
    _seed_state(db_session, "DEV2", NOW - timedelta(hours=2))       # media
    _seed_state(db_session, "DEV3", NOW - timedelta(hours=30))      # alta
    out = wd.run_watchdog(db_session, now=NOW)
    assert db_session.get(HealthDeviceState, "DEV1").transmission_state == "OK"
    assert db_session.get(HealthDeviceState, "DEV2").transmission_severity == "media"
    assert db_session.get(HealthDeviceState, "DEV3").transmission_severity == "alta"
    assert out["evaluated"] == 3


# --- get_no_transmission lista solo los marcados ---
def test_get_no_transmission(db_session):
    _seed_state(db_session, "A", NOW, transmission_state="SIN_TRANSMISION",
                severity="baja")
    _seed_state(db_session, "B", NOW, transmission_state="OK")
    rows = wd.get_no_transmission(db_session)
    assert [r.device_id for r in rows] == ["A"]


# --- _severity_for_gap: fronteras exactas ---
@pytest.mark.parametrize("gap,expected", [
    (0, None), (15, None), (15.1, "baja"), (60, "baja"),
    (60.1, "media"), (1440, "media"), (1440.1, "alta"),
])
def test_severity_fronteras(gap, expected):
    assert wd._severity_for_gap(gap) == expected
