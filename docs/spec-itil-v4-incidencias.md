# SPEC: Gestión de Incidentes y Problemas ITIL v4

**Componentes:** ops-service (incidencias/problemas), iot-service (criticidad equipo), frontend
**Documentos asociados:** `docs/spec-racionalizacion-dashboard-e-incidencias.md` §4, `docs/regla-consolidacion-alertas.md`, `docs/spec-transmision-y-reentrenamiento.md`
**Versión:** 1.1 — BACKEND IMPLEMENTADO (2026-07-05); frontend (I4) pendiente

## Estado
- **Backend (I1-I3, I5): ✅ IMPLEMENTADO y verificado E2E.** Incidentes (ciclo de
  vida + transiciones validadas + SLA + prioridad por matriz), Problemas (CRUD +
  vincular), auto-cierre por el ensemble (finalizado/cancelado) + fallback.
  Gateway routing + RBAC de /problemas. Regresión 367 backend en verde.
- **Frontend (I4): ✅ IMPLEMENTADO (2026-07-05).** Detalle de incidencia (impacto/
  urgencia/categoría, timeline SLA, transiciones válidas, vincular a Problema),
  vista de Problemas (lista + detalle con incidentes), criticidad editable en el
  equipo, nav + RouteGuard. typecheck 0, e2e 40 verde, verificado en navegador.

**ITIL v4 COMPLETO (backend + frontend).**

## Adenda — flujo por rol y calibraciones del técnico (2026-07-05)

Refinamiento del flujo operativo tras feedback:
- **Estado avanza por ACCIÓN, no por dropdown.** Coordinador *Asigna* técnico →
  auto `en_ejecucion`; técnico *Guarda mantenimiento* → auto `resuelto`;
  coordinador *Verifica y cierra* → `finalizado` (+ calibración); *Cancelar* →
  `cancelado`. El detalle de incidencia muestra botones contextuales por rol
  (useAuth). Se eliminó el bug de que asignar exigía llenar el mantenimiento.
- **El técnico también hace calibraciones.** La calibración auto-creada **hereda
  el responsable** de la correctiva (el técnico). `list_calibraciones` filtra por
  responsable cuando el rol es técnico (solo ve las suyas). RBAC: el técnico puede
  **completar** (PUT) pero **no crear** (POST) calibraciones. Nav + RouteGuard
  habilitan `/calibraciones` al técnico; el botón "Nueva Calibración" queda oculto
  para él.

## Objetivo

Elevar la gestión de incidencias del MVP a **Gestión de Incidentes + Problemas
ITIL v4 pragmática**: ciclo de vida formal, priorización por impacto×urgencia,
categorización, SLA, y agrupación de incidentes recurrentes bajo un Problema
(causa raíz). Se construye sobre el modelo de `Incidencia` ya unificado (el RF
fue retirado; el ensemble crea incidencias con `origen`).

## Decisiones tomadas (2026-07-05)
- **Alcance D2 completo:** Incidentes + Problemas (ambos en este track).
- **Impacto** = criticidad del equipo (campo nuevo en `equipos`, iot-service).
  **Urgencia** = severidad del ensemble. **Prioridad** = matriz(impacto × urgencia).
- **Estado `resuelto`** cuenta como ABIERTO: se une a `_OPEN_STATES`
  (`pendiente, en_ejecucion, resuelto`). Dedup de consolidación y watchdog
  siguen tratando el equipo como "en atención" hasta el cierre.
- **Auto-cierre por confirmación del ensemble (§1.1):** `resuelto` NO requiere
  verificación manual. El ensemble confirma el arreglo con datos reales:
  - N lecturas SANO consecutivas → auto `finalizado` (arreglo confirmado) → dispara calibración.
  - Reaparece anomalía → sigue abierto (arreglo falló, queda registrado).
  - 48h sin señal (equipo mudo) → auto `cancelado` (sin confirmar → NO calibración).
    Si el equipo revive con anomalía, la regla C7 crea una incidencia NUEVA (no hay
    lógica de reapertura ad-hoc; cerrar como cancelado ya lo habilita).

---

## 1. Ciclo de vida ITIL

| Estado | Significado | Transiciones válidas desde |
|---|---|---|
| `pendiente` | Nuevo / Registrado (sin o con responsable) | (inicial) |
| `en_ejecucion` | En progreso (técnico trabajando) | pendiente |
| `resuelto` | **NUEVO** — trabajo hecho, pendiente de verificación | en_ejecucion |
| `finalizado` | Verificado y cerrado (dispara calibración auto) | resuelto |
| `cancelado` | Falso positivo / no aplica | pendiente, en_ejecucion |

- Transiciones **no válidas** se rechazan (IT-02): p.ej. `pendiente → finalizado`
  directo, o `finalizado → en_ejecucion`.
- Regla existente conservada: `correctiva finalizado → auto-crea calibración`.
- `_OPEN_STATES = (pendiente, en_ejecucion, resuelto)` — impacta ops (dedup) y
  ml (watchdog); ambos deben usar la nueva tupla.

## 1.1 Auto-cierre por confirmación del ensemble

Cuando el técnico marca `resuelto`, **no** hay verificación manual: el ensemble
confirma el arreglo con datos reales (aprovecha que C1 lo alimenta en vivo). La
comprobación vive en `health_service.evaluate()` (ya procesa cada lectura):

```
al evaluar una lectura de un equipo con incidencia en 'resuelto':
  · si el equipo lleva N_CONFIRM lecturas SANO consecutivas (and_alert=False):
        → ops: transición resuelto → finalizado  (auto, "confirmado por ensemble")
        → dispara auto-calibración (regla existente)
  · si la lectura es anómala (and_alert=True):
        → la incidencia sigue en 'resuelto' (arreglo no confirmado); el conteo
          de confirmación se reinicia. No se crea duplicado (resuelto = abierto).
```

Fallback (equipo mudo): un job del scheduler revisa incidencias en `resuelto`;
si llevan > `RESUELTO_TIMEOUT_H` (48h) sin ninguna lectura (SANO ni anómala),
transición `resuelto → cancelado` con nota "auto-cerrada: sin confirmación del
ensemble (equipo sin datos)". NO dispara calibración. Si el equipo revive con
anomalía, la regla C7 crea una incidencia nueva.

- `N_CONFIRM` configurable (default 6 lecturas ≈ 30 min con muestreo de 5 min).
- La transición auto la ejecuta ml-service llamando a ops (`POST /incidencias/{id}`
  con estado, patrón cross-service ya usado), o ops expone un endpoint dedicado
  `POST /incidencias/{id}/auto-close`. A definir en I2.
- Auto `finalizado` es una transición **válida** desde `resuelto` (misma que la
  manual); auto `cancelado` desde `resuelto` también.

## 2. Priorización: Impacto × Urgencia

**Impacto** (criticidad del equipo, nuevo campo `equipos.criticidad`):
alta | media | baja (default `media`).

**Urgencia** (severidad del ensemble o del origen):
- monitor_salud: CRITICO→alta, EN_RIESGO→media, OBSERVADO→baja
- manual: la que indique el usuario (default media)

**Matriz de prioridad** (ITIL estándar 3×3):

| Impacto \ Urgencia | Alta | Media | Baja |
|---|---|---|---|
| **Alta** | alta | alta | media |
| **Media** | alta | media | baja |
| **Baja** | media | baja | baja |

- La `prioridad` se **deriva** (ya no se asigna directa). Se conservan `impacto`
  y `urgencia` en la incidencia para trazabilidad.
- Escalada (regla C7): al llegar mayor urgencia, se recalcula la prioridad (nunca
  baja automáticamente — se conserva la regla existente de solo-subir).

## 3. Categorización

Campo `categoria`: `sensor | transmision | calibracion | energia | otro`
(default `otro`). El monitor de salud crea con `categoria='sensor'`; el watchdog
(si algún día crea incidencias) usaría `transmision`.

## 4. SLA y tiempos

Timestamps nuevos en `incidencias`:
- `fecha_asignacion` (al setear responsable / pasar a en_ejecucion)
- `fecha_resolucion` (al pasar a resuelto)
- `fecha_cierre` (al pasar a finalizado)

Métricas derivables (para reportes/dashboard): tiempo de asignación, de
resolución, de cierre. Objetivos SLA configurables por prioridad (fase 2 de UI).

## 5. Gestión de Problemas

**Problema** = causa raíz de uno o más incidentes recurrentes.

Tabla nueva `problemas`:
- `id, device_id (opcional), titulo, descripcion, estado (abierto|investigacion|resuelto|cerrado), causa_raiz (text), created_at, updated_at`

Relación: `incidencias.problema_id` (FK opcional a `problemas`).

- **Agrupación (IT-03):** varios incidentes del mismo equipo/categoría pueden
  vincularse a un Problema. Detección sugerida (fase 2): ≥ N incidentes del mismo
  equipo+categoría en una ventana → sugerir crear Problema.
- Resolver un Problema no cierra sus incidentes automáticamente (son ciclos
  distintos), pero da visibilidad de causa raíz.

## 6. Criterios de aceptación
- **IT-01.** Toda incidencia tiene `categoria` e `impacto`/`urgencia`, y su
  `prioridad` se deriva de la matriz.
- **IT-02.** El ciclo de vida rechaza transiciones inválidas.
- **IT-03.** Incidentes pueden agruparse bajo un Problema; se listan sus incidentes.
- **IT-04.** Se registran `fecha_asignacion/resolucion/cierre` para SLA.
- **IT-05.** `origen` se preserva (compatibilidad con dedup de consolidación).
- **IT-06.** `resuelto` cuenta como abierto en dedup (ops) y watchdog (ml).
- **IT-07.** Retrocompatibilidad: incidencias existentes migran con
  `impacto=media, urgencia` derivada de su prioridad actual, `categoria=otro`.
- **IT-08.** Auto-cierre: `resuelto` + N_CONFIRM lecturas SANO → `finalizado`
  automático (dispara calibración). Anomalía en `resuelto` reinicia el conteo.
- **IT-09.** Fallback: `resuelto` + 48h sin lecturas → `cancelado` automático
  (sin calibración). Un equipo que revive con anomalía genera incidencia nueva (C7).

---

## PLAN DE IMPLEMENTACIÓN — CHECKLIST

### FASE I1 — Modelo de datos (ops + iot)
- [ ] **I1.1** iot-service: campo `equipos.criticidad` (alta|media|baja, default media) + migración iot.
- [ ] **I1.2** ops-service: `incidencias` + campos `categoria`, `impacto`, `urgencia`, `fecha_asignacion`, `fecha_resolucion`, `fecha_cierre` + migración ops_006 (backfill IT-07).
- [ ] **I1.3** ops-service: tabla `problemas` + `incidencias.problema_id` (FK opcional) + migración ops_007.
- [ ] **I1.4** Actualizar schemas (IncidenciaCreate/Update/Response) con los campos nuevos.

### FASE I2 — Lógica de negocio (ops-service)
- [ ] **I2.1** `priority_service.derive_priority(impacto, urgencia)` — la matriz 3×3.
- [ ] **I2.2** Transiciones de estado válidas: `VALID_TRANSITIONS`; `update_incidencia` rechaza inválidas (IT-02).
- [ ] **I2.3** Sellado de timestamps SLA al transicionar (asignacion/resolucion/cierre).
- [ ] **I2.4** `create_incidencia` / `create_or_escalate_monitor_incidencia`: derivar prioridad de impacto (criticidad del equipo, vía iot) × urgencia. Conservar la regla de solo-subir en escalada.
- [ ] **I2.5** `_OPEN_STATES` = (pendiente, en_ejecucion, resuelto) en ops **y** ml watchdog (IT-06).
- [ ] **I2.6** `problema_service`: CRUD de problemas + vincular/desvincular incidencias + listar incidentes de un problema.
- [ ] **I2.7** Auto-cierre (IT-08): en `health_service.evaluate()`, si el equipo tiene incidencia en `resuelto`, contar lecturas SANO consecutivas (N_CONFIRM); al llegar → llamar a ops para `resuelto → finalizado`. Anomalía reinicia el conteo. Necesita conocer la incidencia en `resuelto` (consulta a ops) y un contador (reusar `candidate_count`-like en health_device_state o consultar health_readings).
- [ ] **I2.8** Fallback (IT-09): job en scheduler (`RESUELTO_TIMEOUT_H=48`) que cierra como `cancelado` las incidencias en `resuelto` sin lecturas recientes. Flag `AUTOCLOSE_ENABLED`.
- [ ] **I2.9** ops: endpoint/soporte para la transición auto (`auto-close`) distinguiendo auto-finalizado (con calibración) de auto-cancelado (sin).

### FASE I3 — API (ops-service)
- [ ] **I3.1** Endpoints problemas: GET/POST/PUT `/problemas`, GET `/problemas/{id}` (con incidentes).
- [ ] **I3.2** Endpoint vincular: POST `/incidencias/{id}/problema` (asigna problema_id).
- [ ] **I3.3** Exponer campos nuevos en respuestas de incidencia.

### FASE I4 — Frontend
- [ ] **I4.1** Detalle de incidencia: mostrar categoría, impacto/urgencia/prioridad derivada, timeline SLA, botones de transición válidos según estado.
- [ ] **I4.2** Estado `resuelto` en badges y filtros.
- [ ] **I4.3** Vista/sección de Problemas (lista + detalle con sus incidentes) + vincular incidencia a problema.
- [ ] **I4.4** Criticidad del equipo editable en el detalle de equipo.

### FASE I5 — Tests + regresión
- [ ] **I5.1** ops: matriz de prioridad (9 combinaciones impacto×urgencia).
- [ ] **I5.2** ops: transiciones válidas/ inválidas (IT-02).
- [ ] **I5.3** ops: timestamps SLA se sellan en cada transición.
- [ ] **I5.4** ops: `resuelto` cuenta como abierto en dedup (CA-04 con resuelto).
- [ ] **I5.5** ml: watchdog silencia con incidencia en `resuelto` (IT-06).
- [ ] **I5.6** ops: problemas CRUD + agrupación de incidentes (IT-03).
- [ ] **I5.7** Migración IT-07: incidencias viejas quedan consistentes.
- [ ] **I5.8** ml: auto-cierre — N_CONFIRM SANO en `resuelto` → finalizado; anomalía reinicia conteo (IT-08).
- [ ] **I5.9** ml/ops: fallback — `resuelto` + timeout sin lecturas → cancelado, sin calibración (IT-09).
- [ ] **I5.10** Regresión completa (ops + iot + ml + gateway + e2e).

### FASE I6 — Docs
- [ ] **I6.1** Actualizar CLAUDE.md (modelo de incidencias ITIL), BACKLOG (I1-I4 → hecho), MEMORY.

---

## Orden recomendado
I1 (modelo) → I2 (lógica) → I3 (API) → I5 en paralelo por fase → I4 (frontend) → I6 (docs).
Estrategia de testing: baseline verde antes de cada fase; no avanzar con rojos;
regresión completa al cerrar cada fase (igual que en C1-C10).
