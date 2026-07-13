"""Watchdog de pérdida de transmisión (docs/spec-transmision-y-reentrenamiento.md §1).

Job periódico (cada 5 min) que detecta equipos que DEJARON DE ENVIAR lecturas
—el punto ciego del gate reactivo §3.0, que solo ve `valido=0` cuando SÍ llega
una lectura—. Para cada equipo activo mide el gap desde su última lectura y, si
supera el umbral, lo marca `SIN_TRANSMISION` en un canal operativo separado del
canal de salud (CT-03: no ejecuta el ensemble ni penaliza el score).

Silenciamiento (CT-05): un equipo con incidencia abierta en ops (mantenimiento /
correctiva / calibración en curso) no genera `SIN_TRANSMISION` — hay un técnico
trabajándolo y el corte es esperado.
"""
import logging
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.health_state import HealthDeviceState

logger = logging.getLogger(__name__)

IOT_SERVICE_URL = os.environ.get("IOT_SERVICE_URL", "http://iot-service:8001")
OPS_SERVICE_URL = os.environ.get("OPS_SERVICE_URL", "http://ops-service:8003")

TRANSMISSION_OK = "OK"
SIN_TRANSMISION = "SIN_TRANSMISION"
# ITIL: 'resuelto' cuenta como abierto (equipo en atención hasta cierre verificado).
# Debe coincidir con _OPEN_STATES del ops-service.
_OPEN_STATES = ("pendiente", "en_ejecucion", "resuelto")

# Umbrales de gap sin lecturas (muestreo 5 min). §1.2
# 15 min = 3 lecturas perdidas = N_CONSEC del anti-parpadeo.
GAP_TOLERANCE_MIN = 15      # <= 15 min: jitter normal de red, sin alerta
GAP_MEDIA_MIN = 60          # > 1 h
GAP_ALTA_MIN = 24 * 60      # > 24 h


def _severity_for_gap(gap_minutes: float) -> str | None:
    """Severidad de SIN_TRANSMISION por duración del corte (CT-01/CT-02)."""
    if gap_minutes <= GAP_TOLERANCE_MIN:
        return None            # OK, dentro de tolerancia
    if gap_minutes <= GAP_MEDIA_MIN:
        return "baja"
    if gap_minutes <= GAP_ALTA_MIN:
        return "media"
    return "alta"


def _list_active_devices(iot_url: str) -> list[str]:
    """Equipos activos desde iot-service. Fallback: los ya presentes en el estado."""
    try:
        resp = httpx.get(f"{iot_url}/api/v1/iot/equipos", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", [])
        return [
            e["device_id"] for e in items
            if e.get("estado", "activo") == "activo" and e.get("device_id")
        ]
    except Exception:
        logger.exception("Watchdog: no se pudo listar equipos de iot-service")
        return []


def _has_open_incidencia(ops_url: str, device_id: str) -> bool:
    """CT-05: ¿el equipo tiene una incidencia abierta que justifique el silencio?"""
    try:
        resp = httpx.get(
            f"{ops_url}/api/v1/incidencias",
            params={"device_id": device_id, "page_size": "50"},
            timeout=10.0,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return any(i.get("estado") in _OPEN_STATES for i in items)
    except Exception:
        logger.exception("Watchdog: no se pudo consultar incidencias de %s", device_id)
        return False  # ante duda, no silenciar (mejor alertar de más que de menos)


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _clear_to_ok(state: HealthDeviceState, now: datetime) -> bool:
    """Set transmission back to OK if it wasn't. Returns True on change."""
    if state.transmission_state == TRANSMISSION_OK:
        return False
    state.transmission_state = TRANSMISSION_OK
    state.transmission_severity = None
    state.updated_at = now
    return True


def _mark_loss(
    state: HealthDeviceState, severity: str, now: datetime
) -> bool:
    """Mark or escalate SIN_TRANSMISION. Returns True on change."""
    if (state.transmission_state == SIN_TRANSMISION
            and state.transmission_severity == severity):
        return False
    state.transmission_state = SIN_TRANSMISION
    state.transmission_severity = severity
    state.updated_at = now
    return True


def _process_device(
    state: HealthDeviceState,
    device_id: str,
    now: datetime,
    ops_url: str,
) -> tuple[str, dict | None]:
    """Classify a device and mutate its state. Returns (outcome, payload).

    Outcomes: 'ok' | 'cleared' | 'silenced' | 'marked' | 'noop'.
    """
    gap_min = (now - _as_utc(state.last_reading_ts)).total_seconds() / 60.0
    severity = _severity_for_gap(gap_min)

    if severity is None:
        # dentro de tolerancia -> transmision viva; limpiar si marcado (CT-04)
        return ("cleared" if _clear_to_ok(state, now) else "ok"), None

    # gap supera tolerancia. CT-05: silenciar si hay incidencia abierta
    if _has_open_incidencia(ops_url, device_id):
        _clear_to_ok(state, now)
        return "silenced", None

    # marcar / escalar SIN_TRANSMISION (CT-01/CT-02)
    if _mark_loss(state, severity, now):
        return "marked", {
            "device_id": device_id,
            "severity": severity,
            "gap_min": round(gap_min, 1),
        }
    return "noop", None


def run_watchdog(db: Session, now: datetime | None = None,
                 iot_url: str = IOT_SERVICE_URL,
                 ops_url: str = OPS_SERVICE_URL) -> dict:
    """Evalúa la transmisión de todos los equipos activos. Devuelve un resumen.

    Idempotente: se puede correr en cualquier momento; solo persiste cambios de
    estado de transmisión, no toca el canal de salud (CT-03).
    """
    now = _as_utc(now or datetime.now(timezone.utc))
    devices = _list_active_devices(iot_url)
    marked: list[dict] = []
    cleared: list[str] = []
    silenced: list[str] = []
    ok: list[str] = []

    for device_id in devices:
        state = db.get(HealthDeviceState, device_id)
        if state is None or state.last_reading_ts is None:
            # nunca recibimos una lectura de este equipo -> no hay base para el gap
            continue

        outcome, payload = _process_device(state, device_id, now, ops_url)
        if outcome == "marked":
            marked.append(payload)  # type: ignore[arg-type]
        elif outcome == "cleared":
            cleared.append(device_id)
        elif outcome == "silenced":
            silenced.append(device_id)
        elif outcome == "ok":
            ok.append(device_id)
        # 'noop' -> ya estaba SIN_TRANSMISION con misma severidad, sin cambios

    db.commit()
    summary = {
        "evaluated": len(devices),
        "marked": marked,
        "cleared": cleared,
        "silenced": silenced,
        "ok": len(ok),
        "ran_at": now.isoformat(),
    }
    logger.info("Watchdog: %s", summary)
    return summary


def get_no_transmission(db: Session) -> list[HealthDeviceState]:
    """Equipos actualmente en SIN_TRANSMISION (para el panel del dashboard)."""
    return (
        db.query(HealthDeviceState)
        .filter(HealthDeviceState.transmission_state == SIN_TRANSMISION)
        .all()
    )
