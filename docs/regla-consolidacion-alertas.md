# Regla de Negocio: Consolidación de Alertas del Monitor de Salud

**Componente:** Monitor de Salud No Supervisado (ensemble AE+IF+AND)
**Documentos asociados:** `docs/spec-health-monitor-unsupervised.md`, `docs/poc-dashboard-health-monitor.md`
**Versión:** 1.1 — ✅ IMPLEMENTADO y verificado (2026-07-04)

## Objetivo

Reducir la fatiga de alertas (*alert fatigue*) y evitar notificaciones repetitivas al supervisor: consolidar múltiples lecturas anómalas de un mismo equipo en **un único incidente abierto por equipo**, salvo eventos críticos que requieren atención inmediata. Si el equipo ya tiene un incidente abierto del monitor, el técnico ya está enterado — no se crean duplicados.

## Clasificación de lecturas (del ensemble, SPEC §3.5)

| Rango del error | Estado | Severidad | Prioridad de incidente |
|---|---|---|---|
| θ – 2θ | 🟡 Observado | Baja | Baja |
| 2θ – 3θ | 🟠 En Riesgo | Media | Media |
| > 3θ | 🔴 Crítico | Alta | Alta |

Solo las lecturas que pasan la compuerta **AND** (Autoencoder + Isolation Forest coinciden) cuentan como anómalas. `Sano` y `Sin datos` no cuentan.

## Regla de generación de incidentes

### 1. Conteo — ventana FIJA de 24 h con reinicio

Contador **por equipo y por nivel de severidad**, sobre una ventana fija de 24 h. Al cumplirse las 24 h, el contador se reinicia y comienza una nueva evaluación (no es ventana móvil/deslizante).

| Estado | Umbral en la ventana | Dispara |
|---|---|---|
| 🟡 Observado | 5 lecturas | Evaluar creación/escalada |
| 🟠 En Riesgo | 3 lecturas | Evaluar creación/escalada |
| 🔴 Crítico | 1 lectura | Inmediato |

### 2. Creación y dedup — UN incidente abierto por equipo

El dedup es **por equipo** (no por nivel):

- Si el equipo **NO tiene** un incidente correctivo abierto **del monitor de salud** → se **crea** uno, con la prioridad del nivel que disparó.
- Si el equipo **ya tiene** un incidente abierto del monitor → **no se crea otro** (el técnico ya lo conoce).

> "Del monitor de salud" = incidente correctivo originado por el ensemble. Una calibración manual u otra fuente **no** bloquea la creación (Q2: solo los del monitor).

### 3. Escalada — update de prioridad, no nuevo incidente

Si llega un nivel de severidad **mayor** que la prioridad del incidente abierto → se **actualiza la prioridad** del incidente existente (Baja→Media→Alta). **Nunca** se crea un segundo incidente, y **nunca** se baja la prioridad automáticamente.

### 4. Ventana de silencio y reapertura

- La ventana de silencio (dedup) está activa **mientras el incidente del monitor siga abierto** (estado `pendiente` o `en_ejecucion`).
- Si el técnico **cierra** el incidente (`finalizado`/`cancelado`) y el equipo **vuelve a acumular** lecturas anómalas → se puede **crear un incidente nuevo** (Q1: el dedup solo aplica mientras hay uno abierto).
- Al reiniciarse la ventana de 24 h, los contadores por nivel vuelven a cero.

## Criterios de aceptación

**CA-01.** Dado un equipo sin incidente abierto del monitor, cuando se registren **5 lecturas Observado** en 24 h, entonces se crea **un** incidente de prioridad Baja.

**CA-02.** Dado un equipo sin incidente abierto del monitor, cuando se registren **3 lecturas En Riesgo** en 24 h, entonces se crea **un** incidente de prioridad Media.

**CA-03.** Dado un equipo sin incidente abierto del monitor, cuando se registre **1 lectura Crítico**, entonces se crea un incidente de prioridad Alta **inmediatamente**.

**CA-04.** Dado un equipo que **ya tiene** un incidente abierto del monitor, cuando se alcance cualquier umbral de severidad, entonces **no** se crea un incidente adicional.

**CA-05.** Dado un equipo con un incidente abierto de prioridad Baja/Media, cuando llega una lectura de severidad **mayor** (p.ej. Crítico), entonces se **actualiza la prioridad** del incidente existente a la mayor — sin crear uno nuevo.

**CA-06.** Dado un equipo cuyo incidente del monitor fue **cerrado** (finalizado/cancelado), cuando el equipo vuelve a alcanzar un umbral, entonces se puede crear un **nuevo** incidente.

**CA-07.** Dado un equipo con una incidencia de **calibración manual** abierta (no del monitor), cuando alcanza un umbral del monitor, entonces **sí** se crea el incidente del monitor (el dedup solo mira incidentes del monitor).

**CA-08.** El conteo es **independiente por equipo** y **por nivel**: lecturas Observado no suman al contador de En Riesgo ni viceversa.

## Estado: ✅ IMPLEMENTADO (2026-07-04)

Verificado end-to-end en Docker: creación, dedup y escalada de prioridad.
Regresión completa en verde (ops 117, ml 55, iot 21, gateway 69).

### Arquitectura implementada

**Conteo (ml-service `health_service`):**
- Se cuenta sobre `health_readings` con `and_alert=True`, filtrando por `raw_state`
  (estado **crudo** de la lectura, antes del anti-parpadeo §5.1) — no por el estado
  publicado. Esto asegura que las lecturas anómalas reales cuenten aunque el
  semáforo aún no las haya publicado por estabilización.
  - Columna nueva `health_readings.raw_state` (migración `ml_003`).
- **Ventana fija de 24h con reinicio** = bucket alineado a medianoche UTC
  (`_window_start` hace `floor(ts / 24h)`). Todos los equipos reinician a la misma
  hora. Contador independiente por `(device_id, raw_state)` (CA-08).
- Umbrales: `OBSERVADO≥5`, `EN_RIESGO≥3`, `CRITICO≥1` (`ALERT_THRESHOLDS`).
- Al cruzar el umbral, `_maybe_trigger_incidencia` hace `POST` a ops-service
  (**fire-and-forget** con try/except: un fallo de ops **no** rompe la ingesta).

**Creación/escalada (ops-service):**
- Endpoint nuevo: `POST /api/v1/incidencias/monitor-alert` con
  `{device_id, severidad}` → `201 {accion:"created"}`, `200 {accion:"escalated"}`
  o `200 {accion:"noop"}`.
- Lógica en `incidencia_service.create_or_escalate_monitor_incidencia`:
  - **Marca de origen:** columna `incidencias.origen` (migración `ops_005`),
    valores `manual | monitor_salud | prediccion_rul`, default `manual` (backfill).
    El dedup (CA-07) filtra solo `origen='monitor_salud'` + `tipo='correctiva'`.
  - **Dedup por equipo (CA-04):** busca correctiva **abierta** (`pendiente`/
    `en_ejecucion`) del monitor; si existe, no crea otra.
  - **Escalada (CA-05):** solo sube prioridad (baja→media→alta), nunca baja,
    nunca crea segundo incidente.
  - **Reapertura (CA-06):** como solo mira las abiertas, tras cerrar se puede
    crear una nueva.
  - Notificación email en creación y en escalada a `alta` (reusa `email_service`).

Reemplaza la heurística del script de regeneración (`derive_incidencias`, racha
de 6 con `GAP_TOL`) para el flujo en vivo.

### Cobertura de tests

- **ops** `test_incidencias.py::TestConsolidacionMonitorSalud` — CA-01…CA-08
  (creación por nivel, dedup, escalada, no-baja, reapertura, calibración/correctiva
  manual no bloquean, severidad inválida noop).
- **ml** `test_health_service.py` — `_window_start`, `_count_in_window` por nivel,
  disparo CRITICO inmediato, OBSERVADO al 5º, EN_RIESGO al 3º, no-disparo antes del
  umbral / SIN_DATOS / SANO, y que un fallo de ops no rompe `evaluate()`.

### Nota operativa

Los scripts `simulate_*.py` tienen valores etiquetados por estado que, contra el θ
real de cada estación, pueden caer en una banda distinta a su etiqueta (p.ej.
CA-UCHU-01 "OBSERVADO" produce `err≈1.11` → banda EN_RIESGO). Es cosmético (nombres
en el script); el comportamiento del sistema es correcto.
