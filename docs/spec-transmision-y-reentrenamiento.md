# SPEC: Detección de Pérdida de Transmisión + Estrategia de Reentrenamiento

**Componente:** Monitor de Salud No Supervisado (ensemble AE+IF+AND)
**Documentos asociados:** `docs/spec-health-monitor-unsupervised.md`, `docs/regla-consolidacion-alertas.md`
**Versión:** 1.1 (2026-07-04)
**Estado:**
- **Parte 1 (Watchdog de transmisión): ✅ IMPLEMENTADO** y verificado E2E en Docker.
- **Parte 2 (Reentrenamiento): definido, no implementado** (requiere métricas de
  monitoreo persistidas + jobs pesados; se aborda como pieza aparte). El scheduler
  ya existe (APScheduler en ml-service), así que el enganche está listo.

---

# Parte 1 — Detección de Pérdida de Transmisión

## 1.1 Problema

Los equipos operan 24/7 con muestreo cada 5 min. El diseño actual maneja `SIN_DATOS` **solo de forma reactiva**: cuando llega una lectura con `valido=0` (el datalogger reporta "no transmitiendo"). 

**Punto ciego:** si el equipo **deja de enviar lecturas por completo** (datalogger caído, corte de red, PC congelado), el `ml-service` nunca recibe nada → no se entera → la tarjeta queda congelada en el último estado conocido ("Sano" de hace horas). Este es el caso **más común** de un corte real y hoy **no se detecta**.

Se distinguen dos casos:

| Caso | Señal | Detección |
|---|---|---|
| **Transmite pero sin dato válido** | lectura con `valido=0` | ✅ Ya existe → `SIN_DATOS` (gate §3.0) |
| **No transmite nada** | ausencia de lecturas | ❌ Requiere **watchdog** (esta spec) |

## 1.2 Solución — Watchdog de transmisión (job periódico)

Un job que corre cada **5 min** y, para cada equipo activo, evalúa el tiempo desde su última lectura recibida (`health_readings.reading_timestamp` más reciente, o `lecturas_iot`).

### Umbrales (muestreo de 5 min)

| Tiempo sin lecturas | Estado de transmisión | Severidad |
|---|---|---|
| ≤ 15 min (≤ 3 lecturas perdidas) | OK / tolerancia | — (jitter normal de red) |
| > 15 min | `SIN_TRANSMISION` | Baja |
| > 1 h | `SIN_TRANSMISION` | Media |
| > 24 h | `SIN_TRANSMISION` | Alta (extrema) |

- El umbral base de **15 min = 3 lecturas** es coherente con `N_CONSEC=3` del anti-parpadeo del ensemble.
- La escalada por duración reutiliza los buckets del SPEC §8 (low/medium/high/extreme).

### Canal separado (NO es alerta de salud)

`SIN_TRANSMISION` es un **canal operativo**, igual que `SIN_DATOS`:
- **No** ejecuta el ensemble (no hay dato que evaluar).
- **No** entra en el score de "Salud Predictiva".
- Aparece en el panel **"Equipos sin transmisión"** del dashboard (§2.5 del diseño), junto a `SIN_DATOS`.
- Mensaje al usuario: *"Revisar PC / energía / enlace — no es falla del sensor."*

> `SIN_DATOS` (transmite, dato inválido) y `SIN_TRANSMISION` (no transmite) pueden unificarse en la UI bajo "Equipos sin transmisión" — el usuario solo necesita saber "este equipo no está reportando".

## 1.3 Escenarios esperados (sin alerta) — silenciamiento por mantenimiento

Hay periodos donde la ausencia de transmisión es **esperada** y NO debe generar alerta:
- Mantenimiento programado.
- Apagado planificado.
- Calibración en sitio.

**Requiere una pieza nueva:** poder marcar un equipo como **"en mantenimiento"** durante una ventana. Mientras esté marcado:
- El watchdog **no** genera `SIN_TRANSMISION`.
- La regla de consolidación de alertas **no** genera incidentes por ese equipo.

Propuesta mínima: un campo/estado en `equipos` (p.ej. `estado='en_mantenimiento'` con `mantenimiento_hasta` timestamp), o reutilizar una incidencia de tipo mantenimiento abierta como señal de silenciamiento. A definir en implementación.

## 1.4 Criterios de aceptación (transmisión)

**CT-01.** Dado un equipo activo, cuando no se reciben lecturas por > 15 min, entonces el watchdog lo marca `SIN_TRANSMISION` (severidad Baja) y aparece en "Equipos sin transmisión".

**CT-02.** La severidad de `SIN_TRANSMISION` escala a Media (>1h) y Alta (>24h) según el tiempo transcurrido.

**CT-03.** `SIN_TRANSMISION` no ejecuta el ensemble ni penaliza el score de Salud Predictiva.

**CT-04.** Cuando el equipo reanuda la transmisión, el estado se limpia y vuelve a evaluarse por el ensemble (con `hours_since_prev` reseteado, SPEC §4.4).

**CT-05.** Un equipo marcado "en mantenimiento" no genera `SIN_TRANSMISION` ni incidentes mientras dure la ventana de mantenimiento.

## 1.5 Implementación (✅ 2026-07-04) — verificada E2E en Docker

**Scheduler (nuevo):** `app/scheduler.py` — `BackgroundScheduler` de APScheduler
arranca en el startup de FastAPI (ml-service) y corre `run_watchdog` cada 5 min
(`WATCHDOG_INTERVAL_MIN`). Controlado por `WATCHDOG_ENABLED` (default `1`; los
tests lo apagan). Deja el enganche listo para la recalibración de θ (Parte 2).

**Watchdog:** `app/services/watchdog_service.py` — `run_watchdog(db, now)`:
- Lista equipos activos vía iot-service (`GET /iot/equipos`).
- Gap = `now − last_reading_ts` (columna nueva en `health_device_state`, seteada
  por `evaluate()` en cada lectura). Migración **ml_004** añade
  `transmission_state` / `transmission_severity` / `last_reading_ts`.
- Umbrales `_severity_for_gap`: ≤15min OK, >15min baja, >1h media, >24h alta.
- **CT-05 (silenciamiento):** se resolvió reusando el modelo existente — si el
  equipo tiene una **incidencia abierta** (`pendiente`/`en_ejecucion`) en
  ops-service, el watchdog no lo marca (hay un técnico trabajándolo). No se agregó
  campo `en_mantenimiento` a `equipos`.
- **CT-04:** `evaluate()` limpia `SIN_TRANSMISION`→`OK` en cuanto llega una lectura.
- **CT-03:** canal 100% separado; no ejecuta el ensemble ni toca `health_state`.

**API (ml-service, ruteado por el gateway bajo `/api/v1/health-monitor`):**
- `POST /run-watchdog` — corre el watchdog on-demand (debug / cron externo).
- `GET /transmission/no-transmission` — equipos en `SIN_TRANSMISION` (dashboard).
- `GET /{device_id}/state` — ahora incluye `transmission_state`/`severity`/`last_reading_ts`.

**Dashboard:** `EquiposSinTransmision.tsx` unifica ambos canales (`SIN_DATOS` +
`SIN_TRANSMISION`) con badge de motivo ("No transmite" / "Dato inválido") y
severidad.

**Tests:** `tests/test_watchdog.py` (17) — CT-01..CT-05, fronteras de severidad,
multi-equipo, sin last_reading, get_no_transmission. Regresión total 279 en verde.

---

# Parte 2 — Estrategia de Reentrenamiento

## 2.1 Contexto — por qué se necesita (evidencia real)

El SPEC §9 (limitación #2) y el Anexo Técnico (slide 9) ya declararon que un θ fijo tiene límites. La Fase 3 lo **confirmó empíricamente**: `CA-ILO-01` sufrió drift temporal (2024→2025) que bajó su especificidad de 98% a 58% con θ fijo; recalibrar θ la devolvió a 98% (θ pasó de 0.45 a 1.91). El modelo del mundo real **cambia** (cambios de analizador, kits, régimen operativo).

## 2.2 Estrategia híbrida (decisión): programado + por degradación

Dos niveles de actualización, con distinta frecuencia y costo:

### Nivel A — Recalibración de θ (ligera, frecuente)

- **Qué:** recalcular θ por estación sobre una ventana reciente (warm-up), **sin re-entrenar** el AE ni el IF. Ya implementado como `09_recalibrate_theta.py`.
- **Frecuencia:** **mensual** (programado) — barato (< 1 min), no toca los modelos.
- **Por qué:** el drift más común es un corrimiento de nivel (lámpara, flujo) que θ absorbe sin re-entrenar.

### Nivel B — Reentrenamiento completo del ensemble (pesado, condicional)

- **Qué:** re-entrenar AE + IF + scaler por estación sobre datos recientes. Regenera todos los artefactos.
- **Frecuencia:** **trimestral (programado)** **O** disparado por **degradación detectada** (lo que ocurra primero).
- **Por qué:** cuando el cambio es de forma (no solo de nivel) — el "normal" cambió su estructura, no solo su media.

## 2.3 Criterios de decisión para reentrenar (Nivel B por degradación)

Se monitorean métricas en producción; si alguna cruza su umbral → disparar reentrenamiento:

| Señal de degradación | Umbral de disparo |
|---|---|
| **Tasa de alerta** de una estación se dispara | > 3× la tasa base esperada (~5%) sostenida por ≥ 7 días |
| **θ recalibrado** se aleja mucho del θ de entrenamiento | recalibrado > 2× o < 0.5× el θ de train (indica cambio de régimen fuerte) |
| **Especificidad** contra rows normales conocidas cae | < 85% (por debajo del piso operativo; meta era ≥91%) |
| **Cambio físico conocido** (bitácora) | Cambio de analizador / kit / calibración mayor → reentrenar esa estación |

## 2.4 Ventana de datos para reentrenar

- **Nivel A (θ):** warm-up de **2 semanas** recientes (ya usado en Fase 3).
- **Nivel B (modelo):** **últimos 3–6 meses** de operación normal de la estación. Racional:
  - < 3 meses puede no cubrir la variabilidad estacional/operativa.
  - > 6 meses arriesga incluir un régimen viejo ya superado (el problema de Chillón: mezclar regímenes no estacionarios).
  - Se entrena **solo con rows normales** (`valido=1`), como siempre (SPEC §7).

## 2.5 Criterios de aceptación (reentrenamiento)

**CR-01.** La recalibración de θ se ejecuta de forma programada (mensual) por estación, sin re-entrenar los modelos.

**CR-02.** El reentrenamiento completo se ejecuta trimestralmente O cuando una métrica de degradación (2.3) cruza su umbral.

**CR-03.** El reentrenamiento usa 3–6 meses de datos normales recientes de la estación; se registra la ventana usada en el `model_card.json`.

**CR-04.** Tras reentrenar, se compara especificidad nueva vs anterior sobre un holdout; si empeora, se conserva el modelo anterior (no se degrada producción).

**CR-05.** Cada reentrenamiento versiona los artefactos y actualiza `model_version` (trazabilidad ISO 17025).

---

## Notas de implementación (ambas partes)

- **Scheduler:** ambas piezas necesitan ejecución periódica. Opciones: APScheduler dentro del `ml-service`, un cron externo que llame a un endpoint, o un job de CI/CD. No existe hoy.
- **Watchdog** es liviano (query "última lectura por equipo" cada 5 min). **Reentrenamiento** es un job pesado, mejor fuera del request-path (batch nocturno/fin de semana).
- **Métricas de monitoreo** (2.3) requieren persistir la tasa de alerta y especificidad por estación en el tiempo — hoy no se registran. Es prerequisito para el disparo "por degradación".
