# SPEC DOC — Monitor de Salud No Supervisado (Autoencoder + Isolation Forest + AND)

**Proyecto:** Sistema predictivo para reducir las fallas de los equipos de medición directa de calidad de aire (ML + IoT)
**Caso de estudio / dataset base:** `CA-ILO-01` (Estación Bolognesi-Ilo, red OEFA) — con 5 estaciones SO2 adicionales disponibles para validación cruzada (ver §9.1)
**Componente:** Detección de anomalías de salud del equipo (capa ML no supervisada)
**Documento base de diseño:** `Anexo_Tecnico_VigiShield.pptx`
**Versión:** 1.0 — draft para revisión
**Estado:** Especificación (previo a implementación — ver `docs/plan-health-monitor-unsupervised.md`)

---

## 1. Propósito y alcance

Este documento especifica el **componente de detección de anomalías no supervisado** que sustituye al modelo RUL supervisado como núcleo del monitoreo de salud del equipo. El componente se basa en el ensemble descrito en el Anexo Técnico:

> **Autoencoder** (magnitud de la anomalía) **AND** **Isolation Forest** (confirmación) → alerta graduada.

> **Regla de gating fundamental:** el ensemble **solo se evalúa cuando hay transmisión válida** (`SO2_ESTADO = 1`). Cuando no hay transmisión (`SO2_ESTADO = 0`), **no se emite ninguna alerta** ni se calcula severidad — el equipo pasa al estado informativo `SIN_DATOS`. No hay dato que reconstruir, así que ni el Autoencoder ni el Isolation Forest se ejecutan. Ver §3.0.

El alcance de este SPEC cubre:

1. Definición formal del ensemble, sus entradas, salidas y umbrales.
2. La **feature `hours_since_prev`** como reemplazo de `rul_days` (contexto operativo calculable en streaming).
3. El pipeline de entrenamiento (solo con operación normal) y de inferencia (streaming).
4. El contrato de datos entre el datalogger CR310, el `iot-service`, el `ml-service` y el dashboard.
5. Las etiquetas de estado por equipo y su interpretación para el usuario final.

**Fuera de alcance de este SPEC** (documentados aparte):
- La implementación del dashboard → `docs/poc-dashboard-health-monitor.md`.
- El plan de ejecución por fases → `docs/plan-health-monitor-unsupervised.md`.
- Los modelos supervisados Random Forest de la PoC previa (`reports/health_monitor_poc/`) — se conservan como **baseline comparativo**, no como el sistema en producción.

### 1.1 Por qué un enfoque no supervisado

El análisis de factibilidad sobre 17 meses reales de `CA-ILO-01` (`reports/analisis_factibilidad_rul_so2.md`) demostró que **no existen fallas correctivas etiquetadas del analizador** en el periodo: los eventos de `SO2_ESTADO = 0` son mayoritariamente congelamientos del PC industrial, cortes de luz y mantenimientos planificados. Un modelo supervisado de RUL no tiene, literalmente, un fenómeno de degradación que aprender.

El enfoque no supervisado invierte el problema: en lugar de aprender "cómo se ve una falla" (de la que no hay ejemplos), aprende **"cómo se ve la operación normal"** — de la que hay abundancia — y marca como anómalo todo lo que se desvía. Esto es coherente con la limitación reconocida en el Anexo Técnico (slide 9): *"un umbral adaptativo, recalibrado con datos reales de operación, es parte del trabajo futuro."*

---

## 2. Contexto del dataset base — `CA-ILO-01`

> `CA-ILO-01` es el **dataset base** para la v1 del ensemble; hay **6 estaciones SO2 en total** disponibles en `services/ml-proposal/dataset/` (§9.1). El SPEC se especifica sobre `CA-ILO-01` porque es el más largo y mejor caracterizado (17 meses), y el diseño es portable a las otras 5 (features base comunes).

| Propiedad | Valor |
|---|---|
| Estación | `CA-ILO-01` (Bolognesi, Ilo, Moquegua — red OEFA) |
| Analizador de referencia | SO2 Thermo Scientific 43i, serie 1200416204, código interno 61-0028 |
| Datalogger | Campbell CR310 |
| Frecuencia de muestreo | 5 minutos (`BD2_N1_5M`, nivel de validación N1) |
| Cobertura | 17 meses (2024-01 → 2025-06, falta 2025-05) |
| Filas totales | 148 608 · con features completos: 140 310 |
| Delimitador CSV / decimal | Fuente de validación OEFA: `;` / `,` (UTF-8 BOM). **Datasets de `ml-proposal/dataset/`: `,` / `.` (ya normalizados)** — ver §9.1 |
| Zona horaria | Local Perú (UTC-5), tratar como naive |
| Sentinela de inválido | `-9999` |

### 2.1 Variables de entrada del ensemble (grupo SO2)

El ensemble v1 se entrena sobre **5 variables** del analizador SO2 (el Autoencoder las comprime a un cuello de botella de 3, coherente con slide 3):

| # | Variable | Rol | Límite operativo (L2–L3) |
|---|---|---|---|
| 1 | `SO2_PPB` | Concentración medida (contexto) | 1 – 388 ppb |
| 2 | `SO2_FLOW` | Flujo de muestreo (salud) | 0 – 2.5 |
| 3 | `SO2_INTERNAL_TEMP` | Temperatura interna (salud) | 8 – 47 °C |
| 4 | `SO2_LAMP_INT` | Intensidad de lámpara (salud) | 20 – 100 |
| 5 | `hours_since_prev` | Horas desde la última FALLA (contexto operativo) | — (ver §4) |
| *(6)* | *reservado* | Segundo gas / ratio derivado (fase 2 multi-equipo) | — (**no se entrena en v1**) |

> **Decisión (v1):** se entrena con **5 features** → Autoencoder `5 → 3 → 5`. La 6.ª variable (multi-gas) queda **reservada**: el pipeline deja el hook pero no la usa. El Anexo Técnico ilustra el mecanismo con "6 variables"; la implementación base usa 5 y lo documenta en el `model_card.json`. Las columnas extra por-estación (`PMT_VOLTAGE`, `BENCH_*`, `CONV_TEMP`, §9.1) son las candidatas naturales para esa 6.ª feature en una v2.

---

## 3. Arquitectura del ensemble

### 3.0 Gating previo por transmisión (`SO2_ESTADO`) — **antes de todo**

Antes de que el ensemble se ejecute, cada lectura pasa por un **gate de transmisión**:

- Si `SO2_ESTADO = 0` (**sin transmisión**) → el equipo queda en estado `SIN_DATOS`. **No se ejecuta el Autoencoder, no se ejecuta el Isolation Forest, no se calcula severidad y NO se emite ninguna alerta.** Es un estado informativo, no una anomalía.
- Si `SO2_ESTADO = 1` (**con transmisión**) → la lectura entra al ensemble (§3.2 en adelante).

**Racional:** cuando no hay transmisión no existe un vector de features válido que reconstruir — cualquier "anomalía" que se calculara sobre un dato ausente o sentinela (`-9999`) sería espuria. Además, el 67 % de los `SO2_ESTADO = 0` son causas externas al analizador (PC congelado, corte de luz), que no son fallas de salud del sensor y no deben generar alarma de anomalía. La pérdida de transmisión se comunica como `SIN_DATOS` (revisar PC/energía), un canal distinto al de las alertas de salud.

### 3.1 Vista general (del Anexo Técnico, slides 2–13)

```
                     lectura entrante
                            │
                    ┌───────┴────────┐
                    │  ¿SO2_ESTADO?   │   GATE de transmisión (§3.0)
                    └───────┬────────┘
              = 0 (sin tx)  │  = 1 (con tx)
        ┌──────────────────┘└──────────────────┐
        ▼                                       ▼
  ┌────────────┐              lectura (5 features, normalizada)
  │ SIN_DATOS   │                              │
  │ sin alerta  │            ┌─────────────────┴─────────────────┐
  └────────────┘            ▼                                    ▼
                 ┌────────────────────┐              ┌──────────────────────┐
                 │   AUTOENCODER       │              │  ISOLATION FOREST     │
                 │  MLP 5→3→5          │              │  score de aislamiento │
                 │  error = MSE        │              │  contamination = 0.05 │
                 │  θ = percentil 95   │              │  corte = percentil 95 │
                 └─────────┬──────────┘              └───────────┬──────────┘
                           │ error > θ ? (magnitud)             │ anómalo ? (confirmación)
                           └──────────────┬─────────────────────┘
                                          ▼
                                   ┌────────────┐
                                   │  AND gate   │  alerta SOLO si AMBOS coinciden
                                   └──────┬─────┘
                                          ▼
                                graduación por severidad
                           (error vs θ, 2θ, 3θ → Advertencia / Alerta / Crítico)
```

### 3.2 Detector A — Autoencoder (aporta la MAGNITUD)

| Aspecto | Especificación |
|---|---|
| Tipo | Autoencoder no lineal `5 → 3 → 5` implementado con `sklearn.neural_network.MLPRegressor` (una capa oculta de 3 neuronas, reconstruye `X → X`) |
| Entrenamiento | **Solo con operación normal** (rows con transmisión válida — `SO2_ESTADO = 1` / `valido = 1` — y dentro de límites L2–L3) |
| Función de pérdida | MSE de reconstrucción |
| Salida por lectura | `recon_error = mean((x − x̂)², axis=1)` |
| Umbral θ | Percentil 95 del `recon_error` sobre el set de entrenamiento (solo-normal), **por estación** y **configurable** |
| Regla | `error > θ` → candidato a anomalía (aporta severidad al graduar) |
| Framework | `scikit-learn` (ya en `requirements.txt`) — **sin dependencia nueva**, sin TensorFlow/Keras. Persistido con `joblib` |

**Por qué solo-normal:** entrenado únicamente con datos sanos, el AE reconstruye bien lo normal y **falla al reconstruir lo que nunca vio** (una anomalía) → error alto = señal (slide 3).

### 3.3 Detector B — Isolation Forest (aporta la CONFIRMACIÓN)

| Aspecto | Especificación |
|---|---|
| Tipo | `sklearn.ensemble.IsolationForest` |
| `contamination` | `0.05` (hiperparámetro por dominio — slide 9, ver §3.5) |
| `n_estimators` | 200 (a confirmar en tuning) |
| `random_state` | 42 |
| Salida por lectura | score continuo → binarizado por `contamination` (percentil 95) |
| Regla | punto se aísla con pocos cortes → **anómalo** (confirma sí/no) |

### 3.4 Compuerta AND (filtro de falsos positivos)

La alerta se dispara **solo si ambos detectores coinciden** (slide 10):

| Autoencoder (`error > θ`) | Isolation Forest (anómalo) | Resultado |
|---|---|---|
| No | No | Sin alerta |
| Sí | No | Sin alerta (**falso positivo evitado**) |
| No | Sí | Sin alerta (**falso positivo evitado**) |
| Sí | Sí | **ALERTA** |

**Racional (slide 10):** el `OR` dispararía con un solo detector → muchas falsas alarmas. El `AND` exige coincidencia de dos criterios independientes → especificidad reportada 91–93 % (slide 13).

### 3.5 Graduación de severidad (slide 13, §4)

La graduación solo aplica a lecturas que pasaron el gate de transmisión (`SO2_ESTADO = 1`, §3.0). Una vez que la compuerta AND confirma la alerta, la **severidad se lee del error del Autoencoder** respecto a múltiplos de θ:

| Condición | ¿Emite alerta? | Severidad | Etiqueta de estado |
|---|---|---|---|
| `SO2_ESTADO = 0` (sin transmisión) — **gate §3.0** | **No** (ensemble no se ejecuta) | — | `SIN_DATOS` |
| `error ≤ θ` (no pasa AND) | No | — | `SANO` |
| `θ < error ≤ 2θ` **y** AND=Sí | Sí | Advertencia | `OBSERVADO` |
| `2θ < error ≤ 3θ` **y** AND=Sí | Sí | Alerta | `EN_RIESGO` |
| `error > 3θ` **y** AND=Sí | Sí | Crítico | `CRITICO` |

> `SIN_DATOS` es un estado **informativo**, no una alerta de anomalía. No dispara notificación de salud del sensor; a lo sumo alimenta un canal separado de "equipos sin transmisión" (ver §5 y el diseño de dashboard).

> Los umbrales `contamination = 0.05` y `θ = percentil 95` son **hiperparámetros elegidos, no calculados** (slide 9). La justificación por dominio: según bitácoras, los equipos operan normalmente la mayor parte del tiempo; los periodos anómalos son una fracción pequeña (~5 %). Un **umbral adaptativo recalibrado con datos reales** es trabajo futuro explícito.

---

## 4. Feature `hours_since_prev` — reemplazo de `rul_days`

### 4.1 Definición

`hours_since_prev` = **horas transcurridas desde que terminó la última FALLA hasta la lectura actual**.

Donde "FALLA" es la transición `SO2_ESTADO` `1 → 0` (pérdida de transmisión), y "fin de la falla" es el instante en que `SO2_ESTADO` vuelve a `1`.

### 4.2 Por qué reemplaza a `rul_days`

| Criterio | `rul_days` (descartado) | `hours_since_prev` (adoptado) |
|---|---|---|
| Origen | Calculado **manualmente / offline** con conocimiento externo | Calculado desde la propia telemetría |
| Dirección temporal | Requiere conocer eventos **futuros** o etiquetado manual | Solo mira hacia **atrás** (último evento pasado) |
| ¿Lo entrega el CR310? | **No** — nunca vendría en streaming | Implícito: derivable de `SO2_ESTADO` en cada lectura |
| ¿Calculable online? | No (data leakage si se usa como feature) | **Sí** — trivial en streaming |
| Evidencia empírica | — | En la PoC RF fue la **feature #2 más importante** (imp. 0.183) del regresor TTNE |

**Conclusión:** `rul_days` era *data leakage* disfrazado de feature. `hours_since_prev` captura la misma intención ("¿cuánto lleva operando sin interrupción?") pero es honesto: se calcula solo con el pasado, en cada lectura, sin conocimiento del futuro.

### 4.3 Cálculo offline (entrenamiento, muestreo regular)

Coherente con el bloque de referencia (líneas 65–77 del `05_train_m3_ttne.py`), contando filas × 5 min:

```python
hsp = np.full(n, np.nan)   # NaN hasta la primera falla
last_end = None
in_fail = False
for i in range(n):
    if is_fail[i]:
        in_fail = True                       # dentro de una falla
    else:
        if in_fail:
            last_end = i                      # aquí TERMINÓ la falla
        in_fail = False
        if last_end is not None:
            hsp[i] = (i - last_end) * 5 / 60  # filas × 5 min ÷ 60 = horas
```

- Es un contador que se **resetea a 0** cada vez que termina una falla y **crece 5 min por fila** hasta la siguiente.
- Antes de la primera falla → `NaN` (se rellena con la mediana en entrenamiento).

### 4.4 Cálculo online (producción, sobre timestamps reales) — **REQUERIDO**

El cálculo por "filas × 5 min" asume muestreo perfecto. Con el CR310 real hay **huecos** (PC congelado, corte de luz — que además *son* la mayoría de las FALLAS), y `(i - last_end) * 5/60` **subestimaría** el tiempo. En producción **debe** calcularse sobre timestamps:

```python
hours_since_prev = (timestamp_actual - timestamp_fin_ultima_falla).total_seconds() / 3600
```

**Contrato de estado del `ml-service`:** para cada `device_id`, el servicio persiste `timestamp_fin_ultima_falla` (el instante de la última transición `0 → 1`). En cada lectura entrante:
- Si `SO2_ESTADO == 0` (en falla) → no se actualiza; `hours_since_prev` no aplica (estado `SIN_DATOS`).
- Si `SO2_ESTADO == 1` y la lectura previa era `0` → se registra `timestamp_fin_ultima_falla = timestamp_actual`, `hours_since_prev = 0`.
- Si `SO2_ESTADO == 1` y no hay `timestamp_fin_ultima_falla` (nunca hubo falla) → `hours_since_prev = mediana_entrenamiento` (fallback documentado).

### 4.5 Consecuencia de diseño (a documentar en el `model_card.json`)

`hours_since_prev` depende de la definición de FALLA (`SO2_ESTADO` 1→0). El reloj del feature **se resetea con cada pérdida de transmisión, incluidos los PC-freeze**. Esto es deseable: mide "tiempo operando de forma continua desde la última interrupción", que es exactamente la señal de contexto que aporta valor al ensemble.

---

## 5. Etiquetas de estado por equipo

El sistema mantiene **una etiqueta de estado vigente por `device_id`**, derivada de la última lectura procesada por el ensemble:

| Estado | ¿Es alerta? | Origen | Semántica operativa | Color semáforo |
|---|---|---|---|---|
| `SANO` | No | AE `error ≤ θ` | Operación normal, sin acción | 🟢 Verde |
| `OBSERVADO` | Sí | AND=Sí, `θ < error ≤ 2θ` | Desviación leve, vigilar | 🟡 Amarillo |
| `EN_RIESGO` | Sí | AND=Sí, `2θ < error ≤ 3θ` | Anomalía confirmada, planificar intervención | 🟠 Naranja |
| `CRITICO` | Sí | AND=Sí, `error > 3θ` | Anomalía severa, despacho inmediato | 🔴 Rojo |
| `SIN_DATOS` | **No** | `SO2_ESTADO = 0` (gate §3.0) | Sin transmisión (PC/energía/mantenimiento) — **no genera alerta de salud** | ⚫ Gris |

> **`SIN_DATOS` nunca es una alerta.** Al no haber transmisión, el ensemble no se ejecuta (§3.0) y no se emite notificación de anomalía. Es solo un indicador de que el equipo dejó de reportar; su tratamiento (avisar de pérdida de transmisión) es un canal separado y opcional, distinto de las alertas de salud del sensor.

### 5.1 Estabilización (anti-parpadeo)

Para evitar que el semáforo parpadee ante una sola lectura anómala aislada, el estado publicado usa **persistencia mínima**: se requieren **`N_CONSEC = 3` lecturas consecutivas** (15 min) en el mismo nivel antes de promover el estado. La degradación (subir de severidad) puede ser inmediata en `CRITICO`; la mejora (bajar de severidad) requiere `N_CONSEC` lecturas estables. Estos parámetros se exponen como constantes configurables.

**Interacción con `SIN_DATOS`:** la transición a `SIN_DATOS` es **inmediata** apenas `SO2_ESTADO = 0` (no requiere `N_CONSEC`), porque no es una promoción de severidad sino un cambio de canal. Al recuperar transmisión (`SO2_ESTADO` vuelve a `1`), el equipo vuelve a evaluarse por el ensemble desde la primera lectura válida, y el contador anti-parpadeo se reinicia. Un periodo `SIN_DATOS` **no** cuenta como lecturas estables para bajar de severidad.

---

## 6. Contrato de datos (flujo end-to-end)

```
CR310 ──payload JSON──▶ iot-service ──features──▶ ml-service (ensemble) ──estado──▶ api-gateway ──▶ dashboard
```

### 6.1 Entrada al `ml-service` (por lectura)

```json
{
  "device_id": "CA-ILO-01",
  "timestamp": "2025-06-14T10:35:00",
  "so2_ppb": 3.2,
  "so2_flow": 0.41,
  "so2_internal_temp": 31.5,
  "so2_lamp_int": 92.0,
  "so2_estado": 1
}
```

### 6.2 Salida del `ml-service` (por lectura)

**Caso con transmisión (`SO2_ESTADO = 1`)** — el ensemble se ejecutó:

```json
{
  "device_id": "CA-ILO-01",
  "timestamp": "2025-06-14T10:35:00",
  "recon_error": 0.0182,
  "theta": 0.0200,
  "if_anomaly": false,
  "and_alert": false,
  "severity": null,
  "health_state": "SANO",
  "hours_since_prev": 128.5,
  "model_version": "vigishield-ensemble-v1"
}
```

**Caso sin transmisión (`SO2_ESTADO = 0`)** — gate §3.0, ensemble NO se ejecuta, **sin alerta**:

```json
{
  "device_id": "CA-ILO-01",
  "timestamp": "2025-06-14T10:35:00",
  "recon_error": null,
  "theta": 0.0200,
  "if_anomaly": null,
  "and_alert": false,
  "severity": null,
  "health_state": "SIN_DATOS",
  "hours_since_prev": null,
  "model_version": "vigishield-ensemble-v1"
}
```

> Nota: en `SIN_DATOS`, `and_alert` es siempre `false` y `recon_error` / `if_anomaly` son `null` porque los detectores no corren. El consumidor (dashboard, motor de reglas) debe tratar `SIN_DATOS` como estado informativo y **nunca** como disparador de alerta de salud.

### 6.3 Persistencia

Se persiste en una **tabla nueva** en la BD del `ml-service` (tabla `health_state`), no en cache en memoria — así el dashboard puede leer el histórico:

- Serie de `recon_error` + `health_state` por lectura (para el gráfico de tendencia del dashboard).
- Estado vigente por `device_id` (para el semáforo).
- `timestamp_fin_ultima_falla` por `device_id` (para `hours_since_prev`).

---

## 7. Pipeline de entrenamiento (offline)

| Paso | Descripción | Salida |
|---|---|---|
| 1. Carga | Leer los 17 meses de `CA-ILO-01` (`BD2_N1_5M`), parseo robusto (`;`, `,`, BOM), sort + dedup por timestamp | DataFrame único |
| 2. Etiquetado normal | Marcar rows "solo-normal": transmisión válida (`SO2_ESTADO = 1`, o `valido = 1` en los datasets de §9.1) **y** todas las variables dentro de L2–L3 | máscara `is_normal` |
| 3. `hours_since_prev` | Calcular offline (§4.3) sobre el DataFrame ordenado | columna feature |
| 4. Normalización | `StandardScaler` ajustado **solo con rows normales** (persistir el scaler) | `scaler.pkl` |
| 5. Entrenar AE | Entrenar `6→3→6` solo con rows normales; calcular θ = P95 del error | `autoencoder.keras`, `theta.json` |
| 6. Entrenar IF | Ajustar `IsolationForest(contamination=0.05)` sobre rows normales | `iforest.pkl` |
| 7. Validación | Evaluar sobre holdout temporal (últimos 3 meses); reportar especificidad, tasa de alerta, distribución de estados | `metrics.json` |
| 8. Model card | Registrar fecha, hash del dataset, versiones, seed, θ, features | `model_card.json` |

**Split temporal (nunca aleatorio):** Train = 2024-01 → 2025-02 · Test = 2025-03, 2025-04, 2025-06 (idéntico a la PoC RF para comparabilidad directa del baseline).

---

## 8. Métricas de evaluación

Al no haber etiquetas de falla reales, la evaluación es **no supervisada + semi-cualitativa**:

| Métrica | Cómo se mide | Meta |
|---|---|---|
| Especificidad (proxy) | % de rows normales conocidas NO marcadas como alerta | ≥ 91 % (slide 13) |
| Tasa de alerta global | % de rows **con transmisión** (`SO2_ESTADO = 1`) del holdout con `and_alert = True` — las rows `SIN_DATOS` se **excluyen** del denominador | ≈ 5 % (coherente con `contamination`) |
| Falsos positivos ambientales | % de alertas que coinciden con picos ambientales sin señal de salud | Minimizar (regla equipo vs ambiente) |
| Coincidencia con bitácora | ¿Las alertas se agrupan alrededor de eventos conocidos en bitácora? | Cualitativo |
| Comparación vs baseline RF | ¿El ensemble detecta los mismos episodios que M1 (precisión 98 % FALLA)? | Documentar solapamiento |

> El indicador IND 04 (≥ 80 % precisión) se reporta vía el **baseline RF supervisado** (M1 binario, ya cumple con 86.2 %). El ensemble no supervisado se presenta como el **detector en tiempo real** cuya ventaja es no depender de etiquetas de falla — coherente con el argumento de la tesis.

---

## 9. Limitaciones reconocidas

1. **Multi-estación disponible, aún no validada cruzada.** Se dispone de **6 estaciones SO2** de la red OEFA (`services/ml-proposal/dataset/`, ver §9.1) — no una sola. `CA-ILO-01` es el dataset **base** para la v1 del ensemble, pero la generalización entre estaciones (entrenar en unas, validar en otra — *leave-one-station-out*) todavía no se ejecuta y es el siguiente paso natural (ver §9.1 y el plan de implementación). Todas son analizadores SO2, pero con **variaciones de instrumentación** (algunas exponen `SO2_PMT_VOLTAGE`, `SO2_BENCH_TEMP/PRESS`, `SO2_CONV_TEMP`), por lo que un modelo unificado debe entrenarse sobre el **subconjunto común de features** o por-estación.
2. **Umbrales fijos.** `contamination = 0.05` y `θ = P95` son elegidos por dominio, no adaptativos. Recalibración con datos reales = trabajo futuro (declarado en el Anexo Técnico). Con 6 estaciones, θ **puede y debe** calibrarse por-estación (cada analizador tiene su propio nivel de ruido normal).
3. **Sin ground-truth de falla.** La evaluación es semi-cualitativa; no hay recall verificable de "fallas reales del sensor" porque en el periodo analizado de `CA-ILO-01` no hubo ninguna. Las otras 5 estaciones podrían aportar episodios etiquetables (a verificar en EDA multi-estación).
4. **`SIN_DATOS` domina las interrupciones.** El 67 % de los `SO2_ESTADO = 0` (o `valido = 0`, ver §9.1) son externos al analizador (PC/energía). El ensemble no los "predice" — los reporta como pérdida de transmisión, no como anomalía de salud.

### 9.1 Estaciones disponibles (`services/ml-proposal/dataset/`)

| Estación | Nombre | Filas (aprox.) | Columnas de salud adicionales | Flag de validez |
|---|---|---|---|---|
| `CA-ILO-01` | Bolognesi (Ilo) — **base** | 148 608 | — (solo FLOW, INTERNAL_TEMP, LAMP_INT) | `valido` |
| `CA-CH-04` | Grau | 122 688 | `SO2_PMT_VOLTAGE`, `SO2_CONV_TEMP` | `valido` |
| `CA-CH-05` | Garcilaso | 122 688 | `SO2_PMT_VOLTAGE`, `SO2_CONV_TEMP` | `valido` |
| `CA-CHILLO-01` | Chillón | 122 688 | `SO2_PMT_VOLTAGE`, `SO2_BENCH_TEMP`, `SO2_BENCH_PRESS` | `valido` |
| `CA-CC-01` | La Oroya | 69 984 | `SO2_PMT_VOLTAGE`, `SO2_BENCH_TEMP`, `SO2_BENCH_PRESS` | `valido` |
| `CA-UCHU-01` | Uchucarcco | 44 064 | `SO2_PMT_VOLTAGE`, `SO2_BENCH_TEMP`, `SO2_BENCH_PRESS` | `valido` |

**Estructura común (todas):** delimitador `,` (no `;`); columnas `MES, date, SO2_PPB, SO2_FLOW, SO2_INTERNAL_TEMP, SO2_LAMP_INT, valido, rul_days, ciclo_id` + features rolling pre-calculadas (`*_mean/std/trend_{1h,6h,24h}`).

**Notas de compatibilidad con este SPEC:**
- Estos CSV usan `valido` (0/1) como flag de transmisión válida, **no** `SO2_ESTADO`. En estos datasets, el gate §3.0 se aplica sobre `valido` (`valido = 0` ⇒ `SIN_DATOS`). La definición de FALLA de §4.1 se re-mapea a la transición `valido` `1 → 0`.
- Los CSV **incluyen `rul_days`** — es precisamente la columna que se **descarta** como feature (§4.2, *data leakage*). Se reemplaza por `hours_since_prev` derivado de `valido`.
- Las 4 features base del ensemble (`SO2_PPB, SO2_FLOW, SO2_INTERNAL_TEMP, SO2_LAMP_INT`) **existen en las 6 estaciones** → el ensemble base es portable sin cambios; las columnas extra (`PMT_VOLTAGE`, `BENCH_*`, `CONV_TEMP`) son candidatas para la 6.ª feature reservada (§2.1) en estaciones que las tengan.

### 9.2 Evidencia empírica del shift de distribución entre estaciones (Fase 1)

Al construir el dataset (Fase 1 del plan) se confirmó **empíricamente** que los rangos de operación normal **difieren entre estaciones**, validando la decisión de `scaler` y θ **por-estación**:

- **`SO2_LAMP_INT`** en `CA-CH-04` (Grau) y `CA-CH-05` (Garcilaso) opera en torno a **~102** (mediana 101.6–102.1, máx 102.6), **por encima** del `L3 = 100` derivado de `CA-ILO-01` (cuya lámpara opera a mediana ~93.7, máx 96.0). No es degradación: es **otra escala de operación del equipo**.
- Aplicar los límites físicos L2–L3 de Ilo como definición global de "normal" dejaba a Grau y Garcilaso con **0 % de filas normales** (todas sus lecturas caían "fuera de rango" solo por la lámpara), lo que habría hecho imposible entrenar el ensemble para esas estaciones.

**Consecuencia de diseño (aplicada):** la máscara `is_normal` se define como **transmisión válida** (`valido = 1` + features base presentes), **no** por límites físicos globales. Cada estación aprende su propio "normal" desde sus datos (enfoque no supervisado). Con este criterio, las 6 estaciones quedan con **66 %–95 % de filas normales**:

| Estación | % filas normales |
|---|---|
| `CA-ILO-01` | 94.3 % |
| `CA-CC-01` | 95.2 % |
| `CA-CHILLO-01` | 87.5 % |
| `CA-CH-05` | 80.6 % |
| `CA-UCHU-01` | 81.3 % |
| `CA-CH-04` | 66.6 % |

Esto refuerza que un θ global no es apropiado (§9 limitación #2) y anticipa que la **estrategia A (por-estación)** será la robusta; la estrategia B (unificada, leave-one-station-out) deberá demostrar que supera este shift (Fase 3.5 del plan).

---

## 10. Trazabilidad con los objetivos de tesis

| Objetivo / Indicador | Cómo lo cubre este componente |
|---|---|
| OE01 — Seleccionar algoritmos | Autoencoder + Isolation Forest + AND, justificados sobre datos reales |
| OE02 — Diseñar sistema predictivo | Este SPEC + el plan de implementación |
| OE04 — Validar precisión | Especificidad 91–93 % + baseline RF 86.2 % (IND 04) |
| Detección 50 % más rápida | Alerta automática en streaming vs inspección visual periódica |
| Disponibilidad > 95 % | Estado por equipo en tiempo real → despacho dirigido |
| ISO/IEC 17025:2017 | Trazabilidad de estado + `model_card.json` versionado |

---

## Apéndice A — Referencias del repositorio

- Anexo Técnico (fuente de diseño): `Anexo_Tecnico_VigiShield.pptx`
- PoC RF supervisada (baseline): `reports/health_monitor_poc/README.md`
- Factibilidad RUL: `reports/analisis_factibilidad_rul_so2.md`
- Propuesta ML revisada: `reports/propuesta_enfoque_ml_revisado.md`
- Cálculo de referencia de `hours_since_prev`: `services/ml-service/scripts/health_monitor_poc/05_train_m3_ttne.py` (líneas 65–77)
- Spec técnico general: `docs/air-monitoring-spec.md`
