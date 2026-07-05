"""C1 — Ingesta IoT dispara el ensemble de salud (monitor no supervisado).

Cuando iot-service recibe una lectura válida, notifica al ml-service para que el
ensemble (AE+IF+AND) la evalúe en streaming. Esto cierra la cadena
`CR310 → iot ingest → ml evaluate → salud + incidencias` que antes solo se
alimentaba por scripts de simulación (docs/plan-c1-c6-c4-c5.md, gap C1).

Es fire-and-forget: un fallo del ml-service NO rompe la ingesta (la lectura ya
quedó persistida). Se controla con ENSEMBLE_NOTIFY_ENABLED (default on; los tests
lo apagan para no acoplar la ingesta a la red).
"""
import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://ml-service:8002")


def _notify_enabled() -> bool:
    # Se lee dinámicamente para que tests/entornos puedan alternarlo sin re-import.
    return os.environ.get("ENSEMBLE_NOTIFY_ENABLED", "1") == "1"

# Mapeo feature del ensemble -> posibles claves en el payload de sensores.
# El payload real (Thermo) usa mixed-case; toleramos variantes por robustez.
FEATURE_KEYS: dict[str, tuple[str, ...]] = {
    "so2_ppb": ("SO2_ppb", "SO2_PPB", "so2_ppb"),
    "so2_flow": ("SampleFlow", "SO2_flow", "SO2_FLOW", "so2_flow", "sample_flow"),
    "so2_lamp_int": ("UVLampIntensity", "SO2_lamp_int", "SO2_LAMP_INT",
                     "so2_lamp_int", "uv_lamp_intensity"),
    "so2_internal_temp": ("Reaction_Temp", "SO2_internal_temp",
                          "SO2_INTERNAL_TEMP", "so2_internal_temp",
                          "reaction_temp"),
}
_ENSEMBLE_FEATURES = tuple(FEATURE_KEYS.keys())

# Rango físico esperado por feature en la escala OEFA (con la que se entrenó el
# ensemble). Margen amplio para no rechazar variabilidad legítima, pero que
# distingue sin ambigüedad la escala Thermo/CR310 (flow~600, lamp~1940, temp~50).
# Fix del bug de escala C10 (memory/project_c1_scale_bug.md).
OEFA_RANGES: dict[str, tuple[float, float]] = {
    "so2_ppb": (-5.0, 100.0),        # OEFA ~2-9; Thermo da negativos fuertes
    "so2_flow": (0.05, 10.0),        # OEFA ~0.45; Thermo ~600 (discriminador claro)
    "so2_internal_temp": (0.0, 60.0),  # OEFA ~30-35; margen amplio (temp interna varía)
    "so2_lamp_int": (30.0, 300.0),   # OEFA ~102; Thermo ~1940 (discriminador claro)
}


def _in_oefa_scale(features: dict) -> bool:
    """True si las 4 features caen en el rango físico de la escala OEFA.
    Una lectura fuera de rango (p.ej. escala Thermo) produciría recon_error
    absurdo en el ensemble -> se descarta marcándola no-válida (gate §3.0)."""
    for feature, (lo, hi) in OEFA_RANGES.items():
        v = features.get(feature)
        if v is None or not (lo <= v <= hi):
            return False
    return True


def _coerce_number(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):  # bool es subclase de int; no lo queremos
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def map_to_ensemble_features(sensors: dict) -> dict:
    """Extrae los 4 features del ensemble desde el dict de sensores (JSONB).

    Devuelve {so2_ppb, so2_flow, so2_internal_temp, so2_lamp_int, valido,
    scale_ok}. valido=1 solo si las 4 features están presentes, son numéricas Y
    caen en el rango físico de la escala OESA (fix C10). Si falta alguna o la
    escala es incoherente (p.ej. Thermo) -> valido=0 -> el gate §3.0 del ensemble
    lo trata como SIN_DATOS (fallback seguro, evita recon_error absurdo)."""
    sensors = sensors or {}
    out: dict = {}
    for feature, keys in FEATURE_KEYS.items():
        value = None
        for key in keys:
            if key in sensors:
                value = _coerce_number(sensors[key])
                if value is not None:
                    break
        out[feature] = value
    complete = all(out[f] is not None for f in _ENSEMBLE_FEATURES)
    scale_ok = complete and _in_oefa_scale(out)
    out["scale_ok"] = scale_ok
    out["valido"] = 1 if scale_ok else 0
    return out


def _as_iso_utc(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


def notify_ensemble(device_id: str, timestamp: datetime, sensors: dict) -> bool:
    """POST fire-and-forget a ml-service /health-monitor/evaluate.

    Devuelve True si el POST se envió con éxito, False si se omitió o falló.
    NUNCA lanza: la ingesta no debe romperse por un fallo del ensemble."""
    if not _notify_enabled():
        return False

    features = map_to_ensemble_features(sensors)
    scale_ok = features.pop("scale_ok", True)
    if not scale_ok and any(features[f] is not None for f in _ENSEMBLE_FEATURES):
        # había datos pero en escala incoherente (p.ej. Thermo): se envía con
        # valido=0 para que el gate lo trate como SIN_DATOS (fix C10).
        logger.warning(
            "Lectura de %s fuera de la escala OEFA esperada -> valido=0 "
            "(no se evalúa; revisar configuración del datalogger)", device_id
        )
    payload = {
        "device_id": device_id,
        "timestamp": _as_iso_utc(timestamp),
        **features,
    }
    try:
        resp = httpx.post(
            f"{ML_SERVICE_URL}/api/v1/health-monitor/evaluate",
            json=payload,
            timeout=10.0,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception(
            "Error notificando al ensemble para %s (la lectura ya fue persistida)",
            device_id,
        )
        return False
