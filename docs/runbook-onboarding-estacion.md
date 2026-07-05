# Runbook: Onboarding de una Estación Nueva al Monitor de Salud

**Componente:** Monitor de Salud No Supervisado (ensemble AE+IF+AND)
**Documentos asociados:** `docs/spec-health-monitor-unsupervised.md`, `docs/spec-transmision-y-reentrenamiento.md`, `reports/health_monitor_ensemble/multi_station_validation.md`
**Versión:** 1.0 (2026-07-04)
**Estado:** Proceso definido — hoy es **manual** (no automatizado)

## Contexto

El sistema es **por-estación**: cada equipo tiene su propio scaler, Autoencoder, Isolation Forest y umbral θ. Esto es una decisión de diseño fundamentada — cada estación tiene un "normal" físicamente distinto (distinta lámpara, distinto ruido ambiental, distinta estabilidad), por lo que un θ global es incorrecto (ver SPEC §9.1/§9.2). Por eso, una estación nueva **no puede monitorearse hasta que se le entrene un modelo propio o se le asigne uno prestado**.

**Qué pasa hoy si llega una estación sin modelo:** el `health_service` la trata como `SIN_DATOS` (no la evalúa). Es un fallback seguro: no rompe nada, pero tampoco monitorea. Requiere onboarding.

## Con qué θ se entrena — según el histórico disponible

### Escenario A — Estación con histórico (ya operaba antes)

Se entrena directamente con sus propios datos normales.

- **θ:** percentil 95 del error de reconstrucción sobre sus rows normales (`valido=1`).
- **Ventana de datos:** 3–6 meses de operación normal (igual que las 5 estaciones actuales).
- **Es el caso ideal** — el modelo aprende el normal real de esa estación desde el inicio.

### Escenario B — Estación recién instalada (sin histórico)

No hay datos propios todavía. Dos sub-opciones:

**B.1 — Warm-up en sitio (recomendado):**
- Dejar la estación operando **~2 semanas** acumulando lecturas.
- Entrenar su AE+IF y calcular θ con esa ventana warm-up.
- Es lo más preciso; el θ refleja el normal real del equipo.
- **Durante el warm-up, la estación aparece como `SIN_DATOS`** (aún sin modelo) — es esperado.

**B.2 — Modelo prestado (arranque en frío provisional):**
- Usar el modelo unificado (entrenado con las otras estaciones, Estrategia B) como arranque temporal.
- **Solo válido si el régimen de la estación se parece a los ya vistos** — la validación multi-estación mostró que 4 de 5 estaciones generalizan (≥91%), pero una (Ilo, lámpara ~93 vs ~102 de las demás) NO. Si la firma difiere, el modelo prestado dará falsas alarmas.
- Se reemplaza por el modelo propio apenas se complete el warm-up (B.1).

## Quién ajusta el umbral y cuándo

| Momento | Acción | Responsable | Automatizado |
|---|---|---|---|
| **Onboarding inicial** | Entrenar AE+IF + calcular θ propio | Operador técnico (corre scripts) | ❌ Manual |
| **Operación continua** | Recalibrar θ periódicamente (warm-up) | Job programado | ⚠️ Spec definido, no implementado |
| **Cambio de régimen** (cambio de analizador/kit) | Reentrenar modelo | Operador técnico o disparo por degradación | ❌ Manual |

> **Hoy el onboarding es 100% manual.** No existe un flujo/botón "incorporar estación". Es un paso operativo que ejecuta un técnico corriendo los scripts. Automatizarlo es trabajo futuro.

## Procedimiento manual (pasos)

1. **Agregar el equipo** a la BD (`equipos`, con `device_id`, serie, ubicación).
2. **Colocar los datos** de la estación en `services/ml-proposal/dataset/` (o esperar el warm-up si es nueva).
3. **Ejecutar el pipeline** para esa estación (dentro del contenedor, con las versiones correctas — ver nota):
   - `01_build_dataset.py` — construye dataset + `hours_since_prev` + scaler por estación.
   - `02_train_autoencoder.py` — entrena AE + calcula θ.
   - `03_train_iforest.py` — entrena Isolation Forest.
   - `09_recalibrate_theta.py` — (opcional) recalibra θ sobre warm-up reciente.
4. **Verificar** que se crearon los artefactos: `scaler_<sid>.pkl`, `autoencoder_<sid>.pkl`, `iforest_<sid>.pkl`, `theta_<sid>.json`.
5. **Reiniciar/recargar** el `ml-service` para que el registry cargue los nuevos artefactos.
6. **Validar** enviando una lectura normal → debe dar `SANO` con θ coherente.

> **Nota crítica (aprendida en P6):** los artefactos deben entrenarse con las **mismas versiones de numpy/sklearn del contenedor** (numpy 1.26 / sklearn 1.5), no con las del entorno local del desarrollador, o los `.pkl` fallan al cargar. Usar `retrain_in_container.py` como referencia.

## Criterios de aceptación

**CO-01.** Una estación sin modelo se muestra como `SIN_DATOS` (no rompe el sistema, no da falsas alarmas).

**CO-02.** Tras el onboarding (escenario A o B.1), la estación se evalúa con su θ propio y aparece con estado de salud real.

**CO-03.** El θ de una estación nueva se calcula como P95 de su propio error de reconstrucción sobre operación normal — nunca se hereda un θ de otra estación como valor final.

**CO-04.** Si se usa modelo prestado (B.2), se documenta como provisional y se reemplaza al completar el warm-up.

**CO-05.** El `model_card.json` / `theta_<sid>.json` registra la ventana de datos y el origen (histórico propio vs warm-up) para trazabilidad ISO 17025.

## §C8 — Onboarding automático del catálogo (✅ 2026-07-05)

Cuando una estación **no registrada** empieza a enviar lecturas a `POST /iot/readings`,
el sistema ya no la rechaza en seco: la **acoge en cuarentena** automáticamente.

**Flujo:**
1. Llega una lectura con un `device_id` desconocido.
2. **Validación de formato** (`device_onboarding.is_valid_device_id`): debe cumplir el
   patrón de estación OEFA `^(T\d{3}|CA-[A-Z0-9]+-[A-Z0-9]+)$` (los dos esquemas reales:
   `T101`, `CA-UCHU-01`). Si NO cumple (typo/basura) → **404**, no se crea nada (el
   endpoint es público, esto protege el catálogo).
3. Si cumple → se **auto-crea el equipo** con `estado="no_confirmado"` (cuarentena),
   `criticidad="media"` por defecto, resto de metadatos NULL. La lectura se persiste.
4. El equipo en cuarentena **acumula lecturas** pero el ensemble lo reporta `SIN_DATOS`
   (no tiene θ entrenado) → **no dispara incidencias**. Es inofensivo hasta su onboarding.
5. Un **coordinador/admin** lo ve en el panel "Equipos por confirmar" (`GET
   /iot/equipos/pendientes`) y lo **confirma** (`POST /iot/equipos/{id}/confirmar`):
   pasa a `activo`, y de paso asigna criticidad y completa serie/marca/modelo.

**Qué automatiza C8:** el alta del equipo en el catálogo (detección + cuarentena +
aprobación). **Qué sigue siendo manual:** el warm-up y el entrenamiento de θ (escenarios
A/B.1/B.2 de arriba) — un equipo confirmado sigue en `SIN_DATOS` hasta que se le entrena
su θ propio.

**Seguridad:** la validación de formato filtra errores honestos, no actores maliciosos.
El endurecimiento previsto es una **API key por equipo** para autenticar los CR310 (ver
`BACKLOG_POST_MVP.md` §Autenticación, ítem 8).

## Trabajo futuro (automatización del θ)

- Flujo automático del MODELO: estación confirmada → acumular warm-up → entrenar → activar
  θ, sin intervención manual. (C8 ya cubre el alta del catálogo; falta esta pieza del θ.)
- Requiere enganchar el scheduler existente (ver `spec-transmision-y-reentrenamiento.md`).
