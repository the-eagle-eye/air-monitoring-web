"""ITIL I2.7/I2.8 — auto-cierre de incidencias en 'resuelto' por el ensemble.
docs/spec-itil-v4-incidencias.md §1.1.

Job periódico (no en el request-path). Para cada incidencia del monitor en
estado 'resuelto':
  - si el equipo lleva N_CONFIRM lecturas SANO consecutivas → finalizado (auto):
    arreglo confirmado por datos; ops dispara la calibración.
  - si lleva > RESUELTO_TIMEOUT_H sin ninguna lectura (equipo mudo) → cancelado:
    no se pudo confirmar; NO dispara calibración. Si revive con anomalía, la
    regla de consolidación (C7) crea una incidencia nueva.
  - si hay lecturas pero la última es anómala → se deja en 'resuelto' (arreglo
    no confirmado).
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.health_state import HealthReading

logger = logging.getLogger(__name__)

OPS_SERVICE_URL = os.environ.get("OPS_SERVICE_URL", "http://ops-service:8003")
N_CONFIRM = int(os.environ.get("AUTOCLOSE_N_CONFIRM", "6"))
RESUELTO_TIMEOUT_H = int(os.environ.get("RESUELTO_TIMEOUT_H", "48"))


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _resolved_monitor_incidencias(ops_url: str) -> list[dict]:
    """Incidencias correctivas del monitor en estado 'resuelto'."""
    try:
        resp = httpx.get(
            f"{ops_url}/api/v1/incidencias",
            params={"tipo": "correctiva", "estado": "resuelto", "page_size": "200"},
            timeout=10.0,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [i for i in items if i.get("origen") == "monitor_salud"]
    except Exception:
        logger.exception("Auto-cierre: no se pudo listar incidencias resueltas")
        return []


def _recent_readings(db: Session, device_id: str, limit: int):
    """Últimas `limit` lecturas del equipo, más recientes primero."""
    return (
        db.query(HealthReading)
        .filter(HealthReading.device_id == device_id)
        .order_by(HealthReading.reading_timestamp.desc())
        .limit(limit)
        .all()
    )


def _transition(ops_url: str, incidencia_id: int, estado: str, nota: str) -> bool:
    try:
        resp = httpx.put(
            f"{ops_url}/api/v1/incidencias/{incidencia_id}",
            json={"estado": estado, "descripcion": nota},
            timeout=10.0,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Auto-cierre: fallo transición #%s -> %s",
                         incidencia_id, estado)
        return False


def run_autoclose(db: Session, now: datetime | None = None,
                  ops_url: str = OPS_SERVICE_URL) -> dict:
    """Evalúa las incidencias en 'resuelto' y cierra las que corresponda."""
    now = _as_utc(now or datetime.now(timezone.utc))
    finalizadas, canceladas, pendientes = [], [], []

    for inc in _resolved_monitor_incidencias(ops_url):
        device_id = inc["device_id"]
        rows = _recent_readings(db, device_id, N_CONFIRM)

        if not rows:
            # sin lecturas: chequear timeout desde que se resolvió
            resolved_at = inc.get("fecha_resolucion") or inc.get("updated_at")
            if resolved_at:
                try:
                    ts = _as_utc(datetime.fromisoformat(
                        resolved_at.replace("Z", "+00:00")))
                    if (now - ts) > timedelta(hours=RESUELTO_TIMEOUT_H):
                        if _transition(ops_url, inc["id"], "cancelado",
                                       "Auto-cerrada: sin confirmación del "
                                       "ensemble (equipo sin datos)"):
                            canceladas.append(inc["id"])
                            continue
                except ValueError:
                    pass
            pendientes.append(inc["id"])
            continue

        # última lectura anómala -> arreglo no confirmado, dejar en resuelto
        if rows[0].and_alert:
            pendientes.append(inc["id"])
            continue

        # ¿N_CONFIRM lecturas SANO consecutivas (más recientes)?
        confirmadas = [r for r in rows if not r.and_alert]
        if len(rows) >= N_CONFIRM and len(confirmadas) == N_CONFIRM:
            if _transition(ops_url, inc["id"], "finalizado",
                           "Auto-finalizada: arreglo confirmado por el ensemble "
                           f"({N_CONFIRM} lecturas normales)"):
                finalizadas.append(inc["id"])
                continue
        pendientes.append(inc["id"])

    summary = {"finalizadas": finalizadas, "canceladas": canceladas,
               "pendientes": pendientes, "ran_at": now.isoformat()}
    logger.info("Auto-cierre: %s", summary)
    return summary
