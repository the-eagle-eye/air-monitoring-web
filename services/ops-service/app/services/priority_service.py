"""ITIL v4 — priorización por matriz Impacto × Urgencia.
docs/spec-itil-v4-incidencias.md §2.

Impacto = criticidad del equipo. Urgencia = severidad (del ensemble o manual).
La prioridad se DERIVA de la matriz 3×3 (ya no se asigna a mano).
"""

_NIVELES = ("alta", "media", "baja")

# Matriz ITIL estándar 3×3: PRIORITY_MATRIX[impacto][urgencia] -> prioridad
PRIORITY_MATRIX: dict[str, dict[str, str]] = {
    "alta":  {"alta": "alta",  "media": "alta",  "baja": "media"},
    "media": {"alta": "alta",  "media": "media", "baja": "baja"},
    "baja":  {"alta": "media", "media": "baja",  "baja": "baja"},
}

# severidad del ensemble -> urgencia
SEVERITY_URGENCY: dict[str, str] = {
    "CRITICO": "alta",
    "EN_RIESGO": "media",
    "OBSERVADO": "baja",
}

_RANK = {"baja": 1, "media": 2, "alta": 3}


def derive_priority(impacto: str, urgencia: str) -> str:
    """Prioridad = matriz(impacto × urgencia). Valores desconocidos -> 'media'."""
    imp = impacto if impacto in _NIVELES else "media"
    urg = urgencia if urgencia in _NIVELES else "media"
    return PRIORITY_MATRIX[imp][urg]


def urgency_from_severity(severidad: str) -> str:
    """Mapea la severidad del ensemble a urgencia ITIL."""
    return SEVERITY_URGENCY.get(severidad, "media")


def priority_rank(prioridad: str) -> int:
    """Rango numérico para comparar prioridades (escalada solo-sube)."""
    return _RANK.get(prioridad, 0)
