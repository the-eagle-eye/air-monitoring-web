# SPEC: Racionalización del Dashboard + Unificación de Alertas/Incidencias (ITIL v4)

**Componentes:** Frontend dashboard, ml-service (RF legacy + ensemble), ops-service (incidencias)
**Documentos asociados:** `docs/spec-health-monitor-unsupervised.md`, `docs/regla-consolidacion-alertas.md`, `docs/spec-transmision-y-reentrenamiento.md`
**Versión:** 1.2 — §3 IMPLEMENTADO (2026-07-04)
**Estado:** §3 (racionalización) ✅ IMPLEMENTADO y verificado; §4 (ITIL v4) pendiente

## §3 — Implementación completada (rama feat/racionalizacion-dashboard-ensemble)
- **R1 (dashboard):** KpiCards → 4 métricas ensemble; RiskDistributionChart →
  Distribución de Salud (health_state); RecentAlerts → EquiposAtencion (nuevo);
  PredictionTrendsChart → AnomalyTrendsChart (monta ReconErrorChart existente).
  EquipoGrid/EquipoCard sin dependencia RF (fallbacks RiskBadge/BORDER_COLORS quitados).
- **R2 (frontend legacy):** eliminadas páginas `/alertas` y `/predicciones`; nav sin
  esos items; RouteGuard actualizado; eliminados AlertasTable, PrediccionCard,
  PrediccionesTable, RecentAlerts, PredictionTrendsChart, HealthSemaforo, RiskBadge,
  `lib/api/predicciones.ts`, `types/prediccion.ts`. Typecheck limpio.
  dashboard-tecnico + equipos/[deviceId] reescritos a salud (ensemble).
- **R3 (backend, MÍNIMO SEGURO):** `alert_service` ya NO crea incidencias
  (`_notify_ops_alert` → no-op); endpoints `/predictions` y `/alerts` marcados
  `deprecated=True`. El pipeline RF y el modelo .pkl se **conservan** (retiro físico
  total = PR dedicado, para no romper ~40 tests del pipeline). Tests actualizados.
- **Regresión:** 277 tests en verde (ml 70, ops 117, iot 21, gateway 69). Dashboard
  verificado en navegador: sin cards vacías, sin nav legacy, distribución/tendencia OK.

## Decisiones tomadas (2026-07-04)
- **A → A1:** reemplazar cards/secciones RF vacías por métricas del ensemble.
- **B → B1:** un solo concepto = **Incidencia**; se **elimina** el flujo `Alerta`.
- **C → C1:** **retirar el RF** del producto (remover código y endpoints; conservar
  en git history + documentar el porqué).
- **D → D2:** ITIL v4 pragmático (Gestión de Incidentes + Problemas) — track aparte.
- **Orden:** primero §3 completo (R1-R4), luego §4 (ITIL).

---

## 0. Motivación

El sistema migró de un modelo **Random Forest supervisado** (RUL en días, probabilidad
de falla, "alertas" con nivel_riesgo) a un **ensemble no supervisado** (estados de
salud SANO/OBSERVADO/EN_RIESGO/CRITICO + incidencias del monitor). La UI y varias
piezas de backend **arrastran el modelo viejo**, lo que produce:

1. Cards y secciones del dashboard **vacías o con "n/a"** (RUL Promedio, Predicciones,
   Distribución de Riesgo, Alertas Recientes, Tendencia de Predicciones).
2. Dos flujos que hacen lo mismo con distinto nombre: **"Alertas"** (RF) e
   **"Incidencias"** (ensemble/operativo).
3. Confusión conceptual para el usuario y deuda técnica (código muerto).

Además, el usuario quiere que **la gestión de incidencias sea la base para aplicar
ITIL v4** (gestión de incidentes/problemas, ciclo de vida, priorización).

---

## 1. Estado actual (auditoría)

### 1.1 Dashboard — inventario de componentes (`frontend/src/app/dashboard/page.tsx`)

| # | Componente | Fuente de datos | Modelo | Estado observado | Veredicto |
|---|---|---|---|---|---|
| 1 | `SaludPredictivaSemaforo` | `/health-monitor/{id}/state` | **Ensemble** ✅ | "Salud Predictiva: Crítico" | **Mantener** |
| 2 | `EquiposSinTransmision` | `/health-monitor/{id}/state` | **Ensemble+Watchdog** ✅ | 3 equipos sin tx | **Mantener** |
| 3 | `KpiCards` → Total Equipos | iot equipos | neutro ✅ | 5 | **Mantener** |
| 3 | `KpiCards` → Alertas Activas | `/alerts` (RF) | **RF** ❌ | **0** | Reemplazar |
| 3 | `KpiCards` → RUL Promedio | `/predictions` (RF) | **RF** ❌ | **n/a** | Eliminar |
| 3 | `KpiCards` → Predicciones | `/predictions` (RF) | **RF** ❌ | **0** | Eliminar |
| 4 | `EquipoGrid`/`EquipoCard` | ensemble + incidencias | **Ensemble** ✅ | cards con estado | **Mantener** |
| 5 | `RiskDistributionChart` | `/predictions` (RF) | **RF** ❌ | "Sin datos de predicción" | Reemplazar |
| 6 | `RecentAlerts` | `/alerts` (RF) | **RF** ❌ | "Sin alertas recientes" | Reemplazar |
| 7 | `IncidenciasSummary` | ops `/incidencias` | **Operativo** ✅ | 2 correctivas | **Mantener** |
| 8 | `ProximasCalibraciones` | ops `/calibraciones` | **Operativo** ✅ | 0 pendientes | **Mantener** |
| 9 | `PredictionTrendsChart` | `/predictions/{id}` (RF) | **RF** ❌ | "Sin predicciones" | Reemplazar |
| 10 | `SensorTrendsChart` | iot `/lecturas` | neutro ✅ | grilla (datos si hay) | **Mantener** |

> **Conclusión:** 5 piezas puramente RF están **vacías o muertas** en producción:
> RUL Promedio, Predicciones, Distribución de Riesgo, Alertas Recientes, Tendencia
> de Predicciones. "Alertas Activas" muestra 0 porque ya nadie genera alertas RF.

### 1.2 Navegación (`Header.tsx`)

- Items **viejos** en el menú (solo no-técnico): `Predicciones` (`/predicciones`),
  `Alertas` (`/alertas`), `Lecturas` (`/lecturas`).
- `/predicciones` y `/alertas` son páginas RF legacy.

### 1.3 Flujo Alertas (RF) vs Incidencias (ensemble) — el solapamiento

**Cómo funcionaba (RF):**
```
POST /predictions/run  (manual, NO hay scheduler que lo dispare)
  → prediction_service crea Prediccion (RUL, prob_falla, risk_level)
  → alert_service.evaluate_and_create_alert → tabla Alerta (nivel_riesgo)
  → si alta/media → POST ops /incidencias/alert-trigger
       → create_alert_triggered_incidencia (dedup "1 por día", origen=manual)
```

**Cómo funciona ahora (ensemble):**
```
POST /health-monitor/evaluate  (streaming, cada lectura)
  → health_service ensemble → health_state + persistencia
  → regla de consolidación → POST ops /incidencias/monitor-alert
       → create_or_escalate_monitor_incidencia (dedup "1 abierta", origen=monitor_salud)
```

**Hallazgos clave:**
- El RF **no corre solo**: `/predictions/run` es manual, **no hay scheduler** (el único
  scheduler corre solo el watchdog). Por eso hay **0 predicciones y 0 alertas** en la
  BD. El flujo RF está **huérfano**: solo se dispara si el usuario entra a `/predicciones`
  y pulsa "correr". Sin eso → 0 predicciones → 0 alertas → `alert-trigger` nunca se usa.
- **`Alerta` (tabla ml-service) y `Incidencia` (tabla ops-service) modelan lo mismo**
  a distinto nivel de madurez: "algo va mal con un equipo". La `Alerta` es un evento
  crudo; la `Incidencia` es el ticket accionable. Con el ensemble, la regla de
  consolidación **ya produce la Incidencia directamente** — la `Alerta` sobra. El log
  de eventos crudos ya vive en `health_readings` (recon_error, and_alert, severity).
- **GAP ARQUITECTÓNICO (importante):** `iot-service` al recibir una lectura **solo la
  guarda** (`iot.py:34`), **no llama a `/health-monitor/evaluate`**. Hoy el ensemble se
  alimenta **solo por los scripts de simulación** (`scripts/simulate_*.py`). En
  producción real, la ingesta IoT debería disparar el ensemble automáticamente. Ver §7.
- `ReconErrorChart.tsx` (recon_error + θ del ensemble) **ya existe pero no se monta**
  en el dashboard — candidato directo a reemplazar `PredictionTrendsChart`.
- `EquipoCard` tiene **fallbacks RF** (`BORDER_COLORS`, `RiskBadge`) que solo aplican
  si no hay estado de salud — código muerto una vez retirado el RF.
- Existe un tercer servicio, `ml-service-isolation` (backend v3 alternativo por
  episodios, seleccionable por `ML_BACKEND=isolation`, adaptado a shape legacy), otra
  pieza del mismo movimiento de migración. A considerar (§6 pregunta 3).

### 1.4 Modelo de Incidencia actual (base para ITIL)

`incidencias`: `device_id, tipo(correctiva|calibracion), descripcion, estado
(pendiente|en_ejecucion|finalizado|cancelado), prioridad(alta|media|baja),
origen(manual|monitor_salud|prediccion_rul), responsable_id`.
El "trabajo" se registra en `mantenimientos_correctivos` (diagnóstico, acciones,
conclusión, repuestos usados). Auto-reglas: correctiva finalizada → calibración auto.

---

## 2. Decisiones a tomar (con opciones y recomendación)

### Decisión A — ¿Qué hacer con las cards/secciones RF vacías?

| Opción | Descripción | Pros | Contras |
|---|---|---|---|
| **A1 (Recomendada) — Reemplazar por métricas del ensemble** | RUL Promedio → "Horas operando sin corte" (hours_since_prev prom.); Predicciones → "Anomalías 24h"; Distribución de Riesgo → distribución de health_state; Alertas Recientes → "Incidencias recientes del monitor"; Tendencia de Predicciones → tendencia de recon_error/estados | Dashboard 100% coherente con el modelo nuevo, sin huecos | Trabajo de frontend medio |
| A2 — Eliminar sin reemplazo | Quitar las 5 piezas RF | Rápido, menos código | Deja el dashboard más pobre |
| A3 — Dejar como está | No tocar | Cero esfuerzo | Confuso, se ve roto ("n/a", vacíos) |

**Recomendación: A1**, con eliminación limpia de lo que no aporta (RUL/Predicciones
puras) y reemplazo de lo que sí tiene equivalente en el ensemble.

### Decisión B — ¿Unificar Alertas e Incidencias en un solo flujo?

| Opción | Descripción | Pros | Contras |
|---|---|---|---|
| **B1 (Recomendada) — Incidencia como único concepto; retirar Alertas** | Eliminar tabla/página/endpoints `Alerta`. Todo evento accionable es una **Incidencia** con `origen`. El ensemble ya crea incidencias directo. | Un solo modelo mental, base limpia para ITIL, borra código muerto | Hay que migrar/retirar el flujo RF y su UI |
| B2 — Mantener ambos | Dejar Alertas para RF, Incidencias para ensemble | Cero migración | Perpetúa la confusión y el código muerto |
| B3 — Alerta = evento, Incidencia = ticket (jerarquía) | Alerta como log de eventos crudos que alimenta Incidencias | Trazabilidad fina | Sobreingeniería para el MVP; `health_readings` ya es el log de eventos |

**Recomendación: B1.** La `Alerta` RF es redundante: el log de eventos crudos ya
vive en `health_readings` (con recon_error, and_alert, severity), y el ticket
accionable es la `Incidencia`. No necesitamos una capa intermedia.

### Decisión C — Alcance del modelo RF (Random Forest)

| Opción | Descripción | Recomendación |
|---|---|---|
| **C1 (Recomendada) — Retirar RF del producto** | Quitar `/predictions`, `/alerts`, alert_service, la UI y el nav. Conservar el código en git/history y documentar el porqué. | ✅ El ensemble lo reemplazó; el RF nunca corrió en producción (sin scheduler) |
| C2 — Mantener RF como opción | Dejarlo detrás de un flag | Solo si se quiere comparar modelos; añade mantenimiento |

**Recomendación: C1.** Retiro ordenado y documentado.

### Decisión D — Nivel de ITIL v4 a adoptar (sobre Incidencias)

| Opción | Alcance | Recomendación |
|---|---|---|
| D1 — Vocabulario + ciclo de vida básico | Renombrar a lenguaje ITIL (Incidente, prioridad = impacto×urgencia, estados ITIL), mantener el modelo actual | Punto de partida barato |
| **D2 (Recomendada) — Gestión de Incidentes ITIL v4 pragmática** | Ciclo de vida ITIL (Nuevo→Asignado→En progreso→Resuelto→Cerrado), prioridad derivada de impacto×urgencia, categorización, SLA/tiempos, y **distinción Incidente vs Problema** | Aporta valor real de gestión sin sobrecargar |
| D3 — ITIL completo | + Cambios, Activos/CMDB, Conocimiento | Excesivo para el MVP |

**Recomendación: D2** (detallada en §4).

---

## 3. Plan de implementación — Racionalización del dashboard (Decisiones A+B+C)

### Fase R1 — Frontend: dashboard coherente
- [ ] **R1.1** `KpiCards`: reemplazar las 3 cards RF por: **Equipos monitoreados**,
  **Anomalías (24h)** (conteo and_alert), **Incidencias abiertas**, **Sin transmisión**.
- [ ] **R1.2** `RiskDistributionChart` → **Distribución de Salud** (health_state:
  sano/observado/en_riesgo/crítico/sin_datos) desde `healthStates`.
- [ ] **R1.3** `RecentAlerts` → **Incidencias recientes del monitor** (ops
  `/incidencias?origen=monitor_salud`), o retirar (ya está `IncidenciasSummary`).
- [ ] **R1.4** `PredictionTrendsChart` → **Tendencia de anomalías**: montar el
  `ReconErrorChart` **que ya existe** (recon_error + θ por equipo, `fetchHealthReadings`)
  en el dashboard, en su lugar.
- [ ] **R1.5** Quitar del layout las piezas sin reemplazo; reordenar.

### Fase R2 — Frontend: navegación y páginas legacy
- [ ] **R2.1** `Header.tsx`: quitar `Predicciones` y `Alertas` del nav.
- [ ] **R2.2** Eliminar páginas `/predicciones` y `/alertas` (y sus componentes
  `AlertasTable`, `PrediccionCard`, `PrediccionesTable`) — o dejarlas tras flag.
- [ ] **R2.3** Limpiar tipos/APIs muertos (`fetchAlertas`, `fetchPredicciones`,
  `computeKpis`/`computeRiskDistribution` RF en el dashboard).
- [ ] **R2.4** `EquipoCard`: retirar fallbacks RF (`BORDER_COLORS`, `RiskBadge`) una
  vez que el estado de salud es la única fuente.

### Fase R3 — Backend: retiro ordenado del RF (Decisión C1)
- [ ] **R3.1** Marcar `/predictions/*` y `/alerts/*` como deprecated (o remover).
- [ ] **R3.2** `alert_service.evaluate_and_create_alert` y el POST a `/alert-trigger`:
  retirar. La creación de incidencias queda **solo** por `monitor-alert` (ensemble).
- [ ] **R3.3** Decidir sobre `alert-trigger` en ops: mantenerlo si algún cliente
  externo lo usa; si no, retirarlo (lo reemplazó `monitor-alert`).
- [ ] **R3.4** Conservar tabla `Alerta`/`Prediccion` en BD por trazabilidad histórica,
  o migración de retiro. **Documentar** la decisión.
- [ ] **R3.5** Regresión: las 4 suites deben seguir verdes tras el retiro.

### Fase R4 — Documentación
- [ ] **R4.1** Actualizar `docs/CLAUDE.md` (secciones ML Model y Dashboard) al modelo
  ensemble. Documentar el retiro del RF y por qué.
- [ ] **R4.2** MEMORY.

---

## 4. Plan de implementación — ITIL v4 sobre Incidencias (Decisión D2)

> Se especifica aquí a nivel de diseño; la implementación es un track aparte, más grande.

### 4.1 Conceptos ITIL v4 a incorporar

- **Incidente:** interrupción no planificada o degradación de un servicio (equipo).
  Es lo que ya modelamos como `Incidencia` correctiva.
- **Problema:** causa raíz de uno o más incidentes recurrentes (p.ej. una lámpara que
  falla repetidamente). **Nuevo concepto**.
- **Prioridad = Impacto × Urgencia:** hoy la prioridad es directa (alta/media/baja).
  ITIL la deriva de una matriz. El impacto puede venir del rol del equipo (estación
  crítica vs secundaria) y la urgencia de la severidad del ensemble.

### 4.2 Ciclo de vida ITIL (mapeo con estados actuales)

| Estado ITIL | Estado actual | Acción |
|---|---|---|
| Nuevo / Registrado | `pendiente` (sin responsable) | creado por monitor o manual |
| Asignado | `pendiente` (con responsable) | — |
| En progreso | `en_ejecucion` | técnico trabajando |
| Resuelto | (nuevo sub-estado) | trabajo hecho, pendiente de verificación |
| Cerrado | `finalizado` | verificado + calibración auto |
| Cancelado | `cancelado` | falso positivo / no aplica |

### 4.3 Cambios de modelo (propuesta)
- [ ] Campo `categoria` (sensor / transmisión / calibración / energía…).
- [ ] Campos `impacto` y `urgencia`; `prioridad` derivada por matriz.
- [ ] Sub-estado `resuelto` (separar "trabajo hecho" de "verificado/cerrado").
- [ ] Tabla `problemas` + relación `incidencia.problema_id` (opcional, fase 2).
- [ ] Timestamps de SLA: `fecha_asignacion`, `fecha_resolucion`, tiempos objetivo.

### 4.4 Criterios de aceptación (ITIL)
- **IT-01.** Toda incidencia tiene categoría y prioridad derivada de impacto×urgencia.
- **IT-02.** El ciclo de vida sigue transiciones válidas (no saltar de nuevo a cerrado).
- **IT-03.** Incidentes recurrentes del mismo equipo pueden agruparse bajo un Problema.
- **IT-04.** Se registran tiempos (registro→asignación→resolución→cierre) para SLA.
- **IT-05.** El origen (`monitor_salud`/`manual`) se preserva para trazabilidad.

---

## 5. Orden recomendado

1. **§3 (R1–R4)** — racionalización del dashboard e incidencias. **Alto valor,
   bajo riesgo, autocontenido.** Deja la UI coherente y borra el código muerto.
2. **§4 (ITIL v4)** — track separado, más grande, se construye sobre el modelo ya
   limpio de incidencias.

---

## 7. Gap arquitectónico descubierto — ingesta IoT no dispara el ensemble

**No es alcance directo de este spec, pero es crítico y conviene registrarlo.**

Hoy `iot-service` al recibir una lectura (`POST /iot/readings`) **solo la persiste**;
no invoca `/health-monitor/evaluate`. El ensemble se alimenta **exclusivamente por los
scripts de simulación**. En un despliegue real:

- La cadena debería ser: `CR310 → iot-service ingest → (dispara) ml-service evaluate
  → estado de salud + regla de consolidación`.
- Opciones: (a) iot-service hace fire-and-forget POST a evaluate tras guardar; (b) un
  consumer/worker que procese lecturas nuevas; (c) el propio evaluate acepta el payload
  IoT crudo y iot-service lo reenvía.

**Recomendación:** documentar y planificar como pieza aparte (habilita el modo
producción). Mientras, los scripts de simulación cubren demo/testing.

---

## 6. Preguntas abiertas para el usuario

1. **Retiro del RF (C1):** ¿remover código/endpoints, o solo ocultarlos tras flag?
2. **Tablas `Alerta`/`Prediccion`:** ¿migración de retiro o conservar por historia?
3. **`ml-service-isolation`:** ¿sigue vivo como opción, o también se retira?
4. **ITIL alcance (D2):** ¿confirmamos Gestión de Incidentes + Problemas, o
   arrancamos solo con vocabulario/ciclo de vida (D1) y crecemos?
5. **Prioridad de ejecución:** ¿hacemos §3 completo primero, o pieza por pieza?
