# Flujo ITIL v4 — Gestión de Incidentes y Problemas (implementado)

Documento de visualización para el equipo. Describe el flujo **tal como está
implementado** en el sistema (no ITIL genérico). Los diagramas son Mermaid — se
renderizan directo en GitHub/GitLab/VS Code.

> Fuentes: `ops-service/app/services/incidencia_service.py`, `priority_service.py`,
> `mantenimiento_service.py`, `problema_service.py`, `ml-service/app/services/
> health_service.py` + `autoclose_service.py`. Ver también
> `docs/spec-itil-v4-incidencias.md` y `docs/regla-consolidacion-alertas.md`.

---

## 1. Conceptos base

| Concepto | Qué es | Pregunta que responde | Dueño |
|---|---|---|---|
| **Incidente** (Incidencia) | Interrupción/degradación concreta de un equipo | ¿Qué está roto **ahora**? | Técnico (lo repara) |
| **Problema** | Causa raíz de incidentes que se **repiten** | ¿**Por qué** se sigue rompiendo? | Coordinador (lo investiga) |

Un **Problema** agrupa 1..N **Incidencias** (relación 1:N vía `incidencia.problema_id`).

**Roles:**
- **Coordinador / Administrador** — asigna, verifica y cierra, cancela, gestiona
  problemas y calibraciones.
- **Técnico** — registra el mantenimiento correctivo y completa calibraciones; solo
  ve las incidencias asignadas a él.
- **Sistema (monitor de salud)** — crea/escala incidencias automáticamente y auto-cierra.

---

## 2. Ciclo de vida de la Incidencia (máquina de estados)

Cinco estados. Las transiciones están validadas (`VALID_TRANSITIONS`): una transición
inválida devuelve HTTP 400. Cada transición sella un timestamp SLA.

```mermaid
stateDiagram-v2
    [*] --> pendiente: Creada (monitor de salud o manual)

    pendiente --> en_ejecucion: Coordinador ASIGNA técnico<br/>(sella fecha_asignacion)
    pendiente --> cancelado: Coordinador CANCELA

    en_ejecucion --> resuelto: Técnico registra MANTENIMIENTO<br/>(sella fecha_resolucion)
    en_ejecucion --> cancelado: Coordinador CANCELA

    resuelto --> finalizado: Coordinador VERIFICA Y CIERRA<br/>o AUTO-cierre por ensemble<br/>(sella fecha_cierre)
    resuelto --> cancelado: Coordinador CANCELA<br/>o AUTO-cancela (48h sin datos)

    finalizado --> [*]: terminal → dispara calibración
    cancelado --> [*]: terminal (sin calibración)

    note right of en_ejecucion
        Ventana de mantenimiento (C9):
        mientras está en_ejecucion, el
        monitor NO crea ni escala
        incidencias para este equipo
    end note

    note right of resuelto
        "Trabajo hecho, sin verificar".
        Cuenta como ABIERTO (dedup).
    end note
```

**Transiciones — quién y qué las dispara:**

| Transición | Acción que la dispara | Rol | Timestamp |
|---|---|---|---|
| `pendiente → en_ejecucion` | Asignar `responsable_id` (auto-avanza) | Coordinador/Admin | `fecha_asignacion` |
| `en_ejecucion → resuelto` | Técnico envía mantenimiento (`submit_mantenimiento`) | Técnico | `fecha_resolucion` |
| `resuelto → finalizado` | "Verificar y cerrar" **o** auto-cierre por ensemble | Coordinador/Admin **o** sistema | `fecha_cierre` |
| `* → cancelado` | "Cancelar" **o** auto-cancela (48h sin lecturas) | Coordinador/Admin **o** sistema | `fecha_cierre` |

- **Terminal:** `finalizado`, `cancelado`.
- **Abierto** (para dedup): `pendiente`, `en_ejecucion`, `resuelto`.
- **Ventana de mantenimiento** (silencia el monitor): solo `en_ejecucion`.

---

## 3. Flujo end-to-end (nacimiento → cierre)

```mermaid
flowchart TD
    subgraph NACE["① Nacimiento de la incidencia"]
        A1[Lectura IoT ingresada] --> A2{Monitor de salud<br/>ensemble AE+IF}
        A2 -->|anomalía confirmada<br/>and_alert| A3{Umbral en 24h?<br/>OBSERVADO≥5<br/>EN_RIESGO≥3<br/>CRITICO≥1}
        A3 -->|sí| A4[POST /monitor-alert]
        M0[Creación MANUAL<br/>POST /incidencias] --> B1
        A4 --> A5{¿Equipo en ventana<br/>de mantenimiento?<br/>en_ejecucion}
        A5 -->|sí| AX[noop: silenciado]
        A5 -->|no| A6{¿Ya hay correctiva<br/>abierta del monitor?}
        A6 -->|sí| A7[Escala prioridad<br/>nunca crea otra]
        A6 -->|no| B1[Crear Incidencia correctiva]
    end

    subgraph PRIO["② Priorización ITIL"]
        B1 --> P1[impacto = criticidad del equipo]
        P1 --> P2[urgencia = severidad ensemble]
        P2 --> P3[prioridad = matriz impacto × urgencia]
    end

    subgraph CICLO["③ Ciclo de vida"]
        P3 --> C1[pendiente<br/>responsable = coordinador]
        C1 -->|Coordinador ASIGNA técnico| C2[en_ejecucion]
        C2 -->|Técnico registra MANTENIMIENTO| C3[resuelto]
        C3 -->|Coordinador VERIFICA Y CIERRA| C4[finalizado]
        C3 -.->|AUTO: 6 lecturas SANO| C4
        C3 -.->|AUTO: 48h sin lecturas| C5[cancelado]
    end

    subgraph CIERRE["④ Cierre"]
        C4 --> D1[Auto-crea CALIBRACIÓN<br/>hereda al técnico]
        C5 --> D2[Sin calibración]
    end

    style AX fill:#e5e7eb,color:#374151
    style A7 fill:#fef3c7,color:#92400e
    style C4 fill:#dcfce7,color:#166534
    style C5 fill:#fee2e2,color:#991b1b
    style D1 fill:#dbeafe,color:#1e40af
```

**Reglas clave del nacimiento:**
- **Dos orígenes** (`origen`): `monitor_salud` (automático) o `manual`.
- **Regla de consolidación:** un solo incidente correctivo abierto por equipo del
  monitor. Si ya hay uno abierto → **escala prioridad** (nunca baja, nunca duplica).
- **Ventana de mantenimiento (C9):** si el equipo tiene una correctiva `en_ejecucion`
  (técnico interviniendo), el monitor hace **noop total** — las anomalías durante la
  intervención son esperadas.

---

## 4. Matriz de prioridad (impacto × urgencia)

La prioridad **no se fija a mano**: se deriva. El **impacto** viene de la criticidad
del equipo (estación crítica vs secundaria); la **urgencia** de la severidad del
ensemble.

**Severidad del ensemble → urgencia:**

| Severidad | Urgencia |
|---|---|
| `CRITICO` | alta |
| `EN_RIESGO` | media |
| `OBSERVADO` | baja |

**Matriz `prioridad = f(impacto, urgencia)`:**

| impacto ↓ / urgencia → | **alta** | **media** | **baja** |
|---|---|---|---|
| **alta** | 🔴 alta | 🔴 alta | 🟡 media |
| **media** | 🔴 alta | 🟡 media | 🟢 baja |
| **baja** | 🟡 media | 🟢 baja | 🟢 baja |

> Ejemplo: estación crítica (impacto alta) + anomalía OBSERVADO (urgencia baja) →
> prioridad **media**. La prioridad se re-deriva si cambia impacto o urgencia.

---

## 5. Automatizaciones del sistema

```mermaid
flowchart LR
    subgraph AC["Auto-cierre por ensemble (cada 15 min)"]
        R[Incidencia en resuelto<br/>origen=monitor_salud] --> Q{Lecturas recientes?}
        Q -->|6 consecutivas SANO| F[→ finalizado<br/>dispara calibración]
        Q -->|48h sin lecturas| X[→ cancelado<br/>sin calibración]
        Q -->|anomalía| R2[sigue en resuelto]
    end
```

- **Auto-crear calibración:** cuando una correctiva pasa a `finalizado`, se crea
  automáticamente una incidencia de **calibración** que **hereda al técnico** de la
  correctiva (aparece en "sus" calibraciones).
- **Auto-cierre por ensemble** (`autoclose_service`, cada 15 min): una correctiva del
  monitor en `resuelto` se cierra sola cuando el equipo confirma recuperación
  (**6 lecturas SANO consecutivas** → `finalizado`), o se cancela si lleva **48h sin
  lecturas** (→ `cancelado`, sin calibración porque no hubo verificación real).

---

## 6. Incidente vs Problema + detección de recurrencia

```mermaid
flowchart TD
    subgraph HIST["Historial de correctivas por equipo"]
        I1[Correctiva #1<br/>equipo T102]
        I2[Correctiva #2<br/>equipo T102]
        I3[Correctiva #3<br/>equipo T102]
    end

    I1 & I2 & I3 --> DET{Detección de recurrencia<br/>≥3 correctivas en 90 días?}
    DET -->|sí, y sin problema abierto| SUG[Sugerencia en dashboard:<br/>'Equipo reincidente']
    SUG -->|Coordinador pulsa<br/>'Crear problema'| PROB[PROBLEMA<br/>causa raíz]
    PROB -.->|vincula 1:N| I1 & I2 & I3

    PROB --> PE[abierto → investigacion<br/>→ resuelto → cerrado]

    style SUG fill:#fef3c7,color:#92400e
    style PROB fill:#ede9fe,color:#5b21b6
```

- La detección **SUGIERE** (no crea automáticamente): un Problema implica análisis
  humano de la causa raíz. Umbral configurable (por defecto **≥3 correctivas / 90 días**;
  cuenta abiertas + cerradas).
- **Excluye** equipos que ya tienen un Problema `abierto`/`investigacion` (no re-sugiere
  lo ya gestionado).
- Al pulsar "Crear problema", el sistema lo crea **pre-llenado** (equipo + título/descr)
  y **vincula automáticamente** las incidencias recurrentes.
- **Valor para OEFA / ISO 17025:** el Problema es la evidencia documentada de análisis
  de causa y acción correctiva, y habilita decisiones que un incidente aislado no
  permite (reemplazar el equipo, detectar lote defectuoso, ajustar calibración).

**Estados del Problema:** `abierto → investigacion → resuelto → cerrado`.

---

## 7. Cadena entre servicios (secuencia)

```mermaid
sequenceDiagram
    participant CR as CR310 / IoT
    participant IOT as iot-service
    participant ML as ml-service (ensemble)
    participant OPS as ops-service
    participant SCH as ml-service (scheduler)

    CR->>IOT: POST /iot/readings (lectura)
    IOT->>IOT: persiste lectura
    IOT-->>ML: POST /health-monitor/evaluate (fire-and-forget, C1)
    ML->>ML: ensemble AE+IF → estado de salud
    alt anomalía confirmada y cruza umbral 24h
        ML-->>OPS: POST /incidencias/monitor-alert {device_id, severidad}
        OPS->>IOT: GET /iot/equipos/{id} (criticidad = impacto)
        OPS->>OPS: crear/escalar incidencia (prioridad = matriz)
    end

    Note over SCH,OPS: cada 15 min (auto-cierre)
    SCH->>OPS: GET /incidencias?estado=resuelto
    SCH->>ML: consulta lecturas recientes por equipo
    alt 6 lecturas SANO
        SCH-->>OPS: PUT /incidencias/{id} estado=finalizado
        OPS->>OPS: auto-crea calibración
    else 48h sin lecturas
        SCH-->>OPS: PUT /incidencias/{id} estado=cancelado
    end
```

Todas las llamadas cross-service del monitor son **fire-and-forget / tolerantes a
fallos**: si un servicio no responde, la ingesta y el ciclo operativo no se rompen.

---

## 8. Resumen: quién hace qué

```mermaid
flowchart LR
    SIS([🤖 Sistema / Monitor]):::sis
    COORD([👤 Coordinador / Admin]):::coord
    TEC([🔧 Técnico]):::tec

    SIS -->|crea / escala / auto-cierra| INC[Incidencia]
    COORD -->|asigna · verifica y cierra · cancela| INC
    TEC -->|registra mantenimiento| INC
    COORD -->|crea / investiga / vincula| PRB[Problema]
    TEC -->|completa| CAL[Calibración]
    COORD -->|crea| CAL

    classDef sis fill:#e5e7eb,color:#374151
    classDef coord fill:#dbeafe,color:#1e40af
    classDef tec fill:#dcfce7,color:#166534
```

| Acción | Coordinador/Admin | Técnico | Sistema |
|---|:---:|:---:|:---:|
| Crear incidencia (manual) | ✅ | — | — |
| Crear incidencia (monitor) | — | — | ✅ |
| Asignar / Re-asignar técnico | ✅ | — | — |
| Registrar mantenimiento | — | ✅ | — |
| Verificar y cerrar | ✅ | — | ✅ (auto) |
| Cancelar | ✅ | — | ✅ (auto) |
| Crear/gestionar Problema | ✅ | — | (sugiere) |
| Completar calibración | ✅ | ✅ | — |
| Escalar prioridad | — | — | ✅ |

---

*Diagramas fieles a la implementación al 2026-07-05. Si el flujo cambia, actualizar
este documento junto con `docs/spec-itil-v4-incidencias.md`.*
