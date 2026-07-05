"""C8 — Onboarding automático de estaciones nuevas.

Cuando llega una lectura de un `device_id` que no está registrado, en vez de
rechazarla (404) se AUTO-CREA el equipo en CUARENTENA (`estado="no_confirmado"`),
siempre que el `device_id` cumpla el formato esperado de las estaciones OEFA.

Racional (ver docs/runbook-onboarding-estacion.md §C8):
- El endpoint de lecturas es PÚBLICO (los CR310 no autentican), así que el filtro
  de formato evita que un typo (`T10I`) o basura ensucien el catálogo.
- Un equipo recién creado NO tiene modelo/θ del ensemble, por lo que el monitor lo
  reporta como SIN_DATOS y NO dispara incidencias hasta que se entrene su θ. Por eso
  auto-crear es seguro: acumula lecturas sin generar ruido.
- La cuarentena (`no_confirmado`) hace que el coordinador/admin lo apruebe y complete
  sus datos (serie, marca, criticidad) antes de considerarlo operativo (`activo`).

Endurecimiento futuro (backlog): API key por equipo para autenticar los CR310.
"""
import re

# Formato de device_id de las estaciones OEFA. Cubre los dos esquemas reales:
#   - Thermo/laboratorio:  T + 3 dígitos            (T101, T999)
#   - Estación de campo:   CA-<segmento>-<segmento>  (CA-CH-04, CA-CHILLO-01, CA-UCHU-01)
# Rechaza typos y basura: minúsculas (t101), truncados (T10, CA-), inyección, etc.
DEVICE_ID_PATTERN = re.compile(r"^(T\d{3}|CA-[A-Z0-9]+-[A-Z0-9]+)$")

# Estado de cuarentena: el equipo existe y acumula lecturas, pero no es operativo
# hasta que un coordinador/admin lo confirme.
ESTADO_NO_CONFIRMADO = "no_confirmado"
ESTADO_ACTIVO = "activo"


def is_valid_device_id(device_id: str) -> bool:
    """True si el device_id cumple el formato de estación OEFA (apto para onboarding)."""
    return bool(DEVICE_ID_PATTERN.match(device_id or ""))
