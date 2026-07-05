# PoC — Diseño del Dashboard del Monitor de Salud (Ensemble No Supervisado)

**Componente ML asociado:** `docs/spec-health-monitor-unsupervised.md`
**Plan de implementación:** `docs/plan-health-monitor-unsupervised.md`
**Naturaleza de este documento:** diseño de UI/UX **para revisión** — no incluye código todavía.
**Frontend objetivo:** `frontend/` (Next.js, dark theme zinc, Recharts) — reutiliza el lenguaje visual del actual `HealthSemaforo.tsx`.

> Objetivo: mostrar cómo se vería la salida del ensemble (Autoencoder + Isolation Forest + AND) en el dashboard real, cómo se manejan las **etiquetas de estado por equipo**, y cómo se **interpreta** para el usuario operativo (técnico OEFA / coordinador).

---

## 1. Del modelo al usuario — traducción de conceptos

El usuario final **no ve** "error de reconstrucción" ni "score de Isolation Forest". Ve un **semáforo con una etiqueta y una recomendación de acción**. Esta es la tabla de traducción:

| Salida del ensemble | Etiqueta al usuario | Color | Qué debe hacer el técnico |
|---|---|---|---|
| `error ≤ θ` | **Sano** | 🟢 Verde | Nada. Operación normal. |
| AND=Sí, `θ < error ≤ 2θ` | **Observado** | 🟡 Amarillo | Vigilar en la próxima ronda. |
| AND=Sí, `2θ < error ≤ 3θ` | **En riesgo** | 🟠 Naranja | Planificar intervención esta semana. |
| AND=Sí, `error > 3θ` | **Crítico** | 🔴 Rojo | Despacho inmediato al sitio. |
| `SO2_ESTADO = 0` | **Sin datos** | ⚫ Gris | Verificar PC/energía/transmisión (no es falla del sensor). |

**Principio de diseño:** cada estado responde a una sola pregunta del usuario — *"¿tengo que ir, y con qué urgencia?"*. El detalle técnico (error, score, θ) está disponible pero **plegado**, para el analista, no para la decisión operativa.

---

## 2. Manejo de etiquetas por equipo

### 2.1 Modelo de estado

Cada `device_id` mantiene **un estado vigente**, actualizado en cada lectura (cada 5 min), con estabilización anti-parpadeo (`N_CONSEC = 3` lecturas ⇒ 15 min) para no cambiar de color ante un pico aislado.

```
device_id      estado_vigente   error_actual   θ       hours_since_prev   ultima_lectura
CA-ILO-01      Sano             0.0121         0.0200  128.5 h            10:35
T-102          En riesgo        0.0518         0.0200  6.2 h              10:35
T-103          Sin datos        —              —       —                  08:10 (última)
```

### 2.2 Reglas de transición (visibles en tooltip)

- **Escalada** (subir severidad): inmediata al llegar a `Crítico`; requiere `N_CONSEC` para `Observado`/`En riesgo`.
- **Descenso** (bajar severidad): siempre requiere `N_CONSEC` lecturas estables → evita "verde prematuro".
- **`Sin datos`**: se activa apenas `SO2_ESTADO = 0`. Al recuperar transmisión, `hours_since_prev` se resetea a 0 y el equipo vuelve a evaluarse.

### 2.3 Multi-equipo

El diseño escala a N equipos sin cambios: cada tarjeta lee su propio estado.

### 2.4 Semáforo general — **dos indicadores separados** (decisión)

El dashboard muestra **dos semáforos gemelos lado a lado**, no un score combinado:

| Indicador | Fuente | Pregunta que responde |
|---|---|---|
| **Salud predictiva** | Ensemble AE+IF+AND (nuevo) | *"¿algún sensor se está degradando?"* (anticipación) |
| **Estado operativo** | Incidencias abiertas (`HealthSemaforo.tsx` actual) | *"¿qué está en falla/mantenimiento ahora?"* (estado confirmado) |

**Por qué separados y no mezclados:**
1. Miden cosas distintas con acciones distintas: la salud predictiva es anticipación (aún no falla); las incidencias son estado presente confirmado (ya hay ticket). Un score único los volvería indistinguibles.
2. **Trazabilidad ISO 17025:** el auditor necesita ver por separado qué dijo el modelo y qué acción operativa se tomó.
3. **Evita doble conteo:** cuando una anomalía crítica del ensemble *genera* una incidencia correctiva (regla de negocio #6), un score único penalizaría el equipo dos veces.
4. **Extiende lo existente:** el `HealthSemaforo.tsx` actual queda como **"Estado operativo"**; se añade **"Salud predictiva"** al lado.

**Cómputo del score de "Salud predictiva"** (agrega los estados del ensemble por equipo):

| Estado ensemble | Peso en score de salud predictiva |
|---|---|
| Sano | 0 (no penaliza) |
| Observado | −15 |
| En riesgo | −25 |
| Crítico | −40 |
| Sin datos | **excluido del cómputo** (ver §2.5) |

> **`Sin datos` NO entra en el score de salud predictiva** — al no haber transmisión, el ensemble no se ejecutó, así que ese equipo no tiene "salud medida". Se contabiliza aparte en la lista "Equipos sin transmisión" (§2.5). Esto es coherente con el SPEC §3.0/§8: las rows `SIN_DATOS` se excluyen de las métricas de salud.

### 2.5 `Sin datos` — lista separada "Equipos sin transmisión" (decisión)

Los equipos en `SIN_DATOS` (gris) **no se mezclan** con las tarjetas de salud ni penalizan el semáforo de salud predictiva. Se agrupan en un **panel aparte "Equipos sin transmisión"** con su propia lista y contador:

```
┌──────────────────────────────────────────────┐
│  ⚫ Equipos sin transmisión (2)                │
├──────────────────────────────────────────────┤
│  T-103 · Grau        última lectura: 08:10     │
│  T-107 · Oroya       última lectura: ayer 22:4 │
│  → Revisar PC / energía / enlace (no es falla  │
│    del sensor)                                 │
└──────────────────────────────────────────────┘
```

Racional: `SIN_DATOS` es un canal operativo distinto (pérdida de transmisión: PC/energía), no una alerta de salud. Separarlo mantiene el semáforo de salud limpio y evita que un corte de luz se lea como "equipo enfermo".

---

## 3. Mockups (layout ASCII)

### 3.1 Tarjeta de equipo (vista de grilla del dashboard)

```
┌──────────────────────────────────────────────┐
│  CA-ILO-01 · Bolognesi-Ilo         🟢 SANO    │
│  SO2 Thermo 43i · 61-0028                      │
│                                                │
│  Salud reconstrucción  ▁▁▂▁▁▂▁▁  (bajo θ) ✓    │
│  Operando sin corte:   128.5 h                 │
│  Última lectura:       10:35                   │
│                                    [ Detalle ▸]│
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│  T-102 · Pacocha                  🟠 EN RIESGO │
│  SO2 Thermo 43i · 61-0031                      │
│                                                │
│  Salud reconstrucción  ▂▃▅▆▅▇▆█  (2θ–3θ) ⚠     │
│  Operando sin corte:   6.2 h                   │
│  Acción sugerida:  Planificar intervención     │
│                                    [ Detalle ▸]│
└──────────────────────────────────────────────┘
```

### 3.2 Panel de detalle del equipo (pestaña "Salud")

```
┌───────────────────────────────────────────────────────────┐
│  T-102 · Estado de salud                       🟠 EN RIESGO │
├───────────────────────────────────────────────────────────┤
│                                                             │
│  Error de reconstrucción (últimas 24 h)                     │
│   0.06 ┤                                    ╭─╮   ← actual  │
│        │                              ╭─────╯ ╰─            │
│   0.04 ┤· · · · · · · · · · · 3θ · · ╱· · · · · · · · ·     │
│        │                        ╭───╯                       │
│   0.02 ┤· · · · · · · θ · · ╭──╯ · · · · · · · · · · · ·     │
│        │        ╭──────────╯                                │
│   0.00 ┤────────╯                                           │
│        └─────────────────────────────────────────────────  │
│         00h    06h    12h    18h    24h                     │
│                                                             │
│  Detectores (¿por qué se disparó la alerta?)                │
│   • Autoencoder:      error 0.0518  >  θ 0.0200   ✓ magnitud│
│   • Isolation Forest: anómalo (percentil 97)      ✓ confirma│
│   • Compuerta AND:    AMBOS coinciden  →  ALERTA REAL       │
│                                                             │
│  Contexto operativo                                         │
│   • Operando sin corte: 6.2 h  (se reinició hace 6 h)       │
│   • Variable más desviada: SO2_LAMP_INT (fuera de rango)    │
│                                                             │
│  Acción sugerida:  Planificar intervención esta semana      │
└───────────────────────────────────────────────────────────┘
```

### 3.3 Explicación de la compuerta AND (tooltip educativo)

Reutiliza la tabla del Anexo Técnico (slide 10) como micro-tooltip al pasar sobre "AND":

```
¿Por qué confío en esta alerta?
Dos detectores independientes tuvieron que coincidir:
  Autoencoder dice "raro por magnitud"  +  Isolation Forest dice "raro por aislamiento"
Si solo uno se activara, NO habría alerta (así se evitan falsas alarmas).
```

---

## 4. Interpretación para el usuario — guía por rol

### 4.1 Técnico de campo (OEFA)

- **Lo que ve primero:** el color y la palabra. Verde = sigo mi ronda; Naranja/Rojo = este equipo entra a mi lista de hoy.
- **Gráfico de `recon_error` con línea θ:** **visible para el técnico también** (decisión — todos los roles). No necesita entender el MSE; el gráfico le muestra visualmente si la desviación va subiendo o es estable, lo que ayuda a decidir la urgencia. La línea θ le da la referencia de "a partir de aquí es anómalo".
- **`Sin datos` ≠ falla:** el equipo aparece en la lista separada "Equipos sin transmisión" (§2.5), no como tarjeta enferma. Gris = "dejó de transmitir" (revisar PC/energía), no "el sensor se dañó". El 67 % de las interrupciones históricas fueron externas al analizador.
- **`hours_since_prev` traducido:** "Operando sin corte: 6.2 h" le dice cuánto lleva estable desde la última interrupción — contexto útil para saber si una anomalía es sobre un equipo recién reiniciado.

### 4.2 Coordinador / auditor (ISO 17025)

- **Dos semáforos separados (§2.4):** "Salud predictiva" vs "Estado operativo" — trazabilidad de qué dijo el modelo vs qué acción operativa se tomó, sin mezclarlos.
- **Histórico de estados:** trazabilidad de cuándo cada equipo estuvo en cada estado.
- **Panel de detalle con los dos detectores:** evidencia auditable de *por qué* se emitió una alerta (magnitud + confirmación), no una caja negra.
- **`model_version`** visible en el detalle → trazabilidad del modelo que produjo el estado.

### 4.3 Qué NO se muestra (para no confundir)

- No se muestra un "RUL en días" ni "probabilidad de falla en %" para el ensemble — el sistema **no** predice tiempo exacto de falla (no tiene datos para hacerlo honestamente). Se muestra **estado presente + tendencia del error**, que es lo que el modelo sí sabe.

---

## 5. Datos que consume el dashboard (contrato)

Del endpoint de inferencia (SPEC §6.2), por equipo:

| Campo UI | Origen |
|---|---|
| Color + etiqueta | `health_state` |
| Sparkline / gráfico de tendencia | serie de `recon_error` + `theta` |
| "Operando sin corte: X h" | `hours_since_prev` |
| Detectores (AE / IF / AND) | `recon_error > theta`, `if_anomaly`, `and_alert` |
| Severidad | `severity` |
| Trazabilidad | `model_version`, `timestamp` |

---

## 6. Alcance de esta PoC de dashboard

**Incluye (documento):** traducción modelo→usuario, manejo de etiquetas por equipo, mockups, guía de interpretación por rol, contrato de datos.

### 6.1 Implementación (P5 — hecha 2026-07-04)

Los componentes clave del diseño ya están implementados y conectados al endpoint de Fase 4:

| Componente | Archivo | Estado |
|---|---|---|
| Semáforo "Salud predictiva" (§2.4) | `frontend/src/components/dashboard/SaludPredictivaSemaforo.tsx` | ✅ |
| Lista "Equipos sin transmisión" (§2.5) | `frontend/src/components/dashboard/EquiposSinTransmision.tsx` | ✅ |
| Badge de estado reutilizable | `frontend/src/components/dashboard/HealthStateBadge.tsx` | ✅ |
| Tipos + config visual | `frontend/src/types/healthMonitor.ts` | ✅ |
| Cliente API | `frontend/src/lib/api/healthMonitor.ts` | ✅ |
| Integración en dashboard (2 semáforos lado a lado) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| **Tarjetas de equipo con estado de salud (§3.1)** | `frontend/src/components/dashboard/EquipoCard.tsx` + `EquipoGrid.tsx` | ✅ |
| Ruteo del gateway a `/api/v1/health-monitor` | `services/api-gateway/app/routes/proxy.py` | ✅ |

Los dos semáforos ("Salud predictiva" vs "Estado operativo") se renderizan lado a lado (grid 2-col), y la lista de equipos sin transmisión debajo — coherente con las decisiones §2.4/§2.5. TypeScript sin errores en los archivos nuevos.

**Implementado (P5b, 2026-07-04):** gráfico de `recon_error` + línea θ (§3.2) y tab **"Salud"** en `/equipos/[deviceId]`:
- `frontend/src/components/dashboard/ReconErrorChart.tsx` — línea de error + `ReferenceLine` θ (Recharts dynamic).
- Endpoint `GET /api/v1/health-monitor/{device_id}/readings` (serie histórica) + `fetchHealthReadings` en el cliente.
- Tab "Salud" con badge de estado actual + gráfico. Visible a todos los roles (§7.2).

**Pendiente (post-MVP):** panel de detalle de los dos detectores (AE/IF/AND) por lectura seleccionada (§3.2 mockup completo).

**Reutilización directa:** el `HealthSemaforo.tsx` existente (colores verde `#22c55e` / amarillo `#eab308` / rojo `#ef4444`, patrón de tarjeta, dark theme) quedó como el semáforo de "Estado operativo"; los nuevos componentes extienden ese lenguaje visual.

---

## 7. Decisiones de diseño (resueltas — 2026-07-04)

1. **Semáforo general → dos indicadores separados** ("Salud predictiva" vs "Estado operativo"), no un score combinado. Ver §2.4 para el racional completo (miden cosas distintas, trazabilidad ISO 17025, evita doble conteo, extiende el `HealthSemaforo.tsx` existente).
2. **Gráfico de `recon_error` con línea θ → visible a todos los roles.** El técnico también lo ve (§4.1); no requiere entender el MSE, el gráfico comunica visualmente tendencia y umbral.
3. **`Sin datos` (gris) → lista separada "Equipos sin transmisión"** (§2.5). No se integra en las tarjetas de salud ni penaliza el semáforo de salud predictiva.
