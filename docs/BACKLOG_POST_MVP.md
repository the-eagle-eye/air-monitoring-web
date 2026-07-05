# Backlog Post-MVP

Items planificados para implementacion posterior. Actualizado 2026-07-04.

---

## 🔴 CRÍTICO — Monitor de Salud (ensemble AE+IF+AND)

Pendientes del sistema de monitoreo predictivo. Ordenados por impacto. Los ✅ ya
están implementados y verificados; se listan para dar contexto.

### Gaps que bloquean el modo producción real

| # | Item | Estado | Notas |
|---|---|---|---|
| C1 | **Ingesta IoT → dispara el ensemble** | ✅ HECHO (2026-07-04) | `iot-service` al persistir una lectura hace `POST` fire-and-forget a `ml-service /health-monitor/evaluate` (`ensemble_notify_service`), mapeando claves Thermo → features del ensemble. Flag `ENSEMBLE_NOTIFY_ENABLED`. La cadena `CR310 → iot ingest → ml evaluate → salud + incidencias` quedó cerrada. Verificado E2E. Tests en `test_ensemble_notify.py` (12). |
| C2 | **Retiro físico total del RF** | ✅ HECHO (2026-07-05) | Se eliminaron por completo del ml-service: `prediction_service`, `alert_service`, `model_interface`, `v2_interface`, pipeline RF (`train_model`, `feature_engineering`, `synthetic_data`, `real_data_loader`), routers `/predictions` y `/alerts`, modelos ORM `Prediccion`/`Alerta` + schemas, artefactos `ml_artifacts*` (RF v1/v2/v2.1/health_monitor/backups) y wiring Docker. Migración `ml_006` suelta las tablas `predicciones`/`alertas` (no se borra `ml_001` = raíz de la cadena alembic). Cross-service: gateway `/kpis` sin bloque `alertas`, ops sin `/alert-trigger`/`/evaluar`/`evaluate_alerts`/`create_alert_triggered_incidencia`/`_deactivate_device_alerts`, `origen` sin `prediccion_rul`, email correctiva reescrito a lenguaje ensemble. **`ml-service-isolation` (v3 AE+IF) NO es RF → intacto**; el gateway conserva `ML_BACKEND=isolation` que sí usa `/predictions`+`/alerts`. Regresión: 334 backend verde (−42 tests, todos RF). |

### Detección de transmisión y reentrenamiento (`docs/spec-transmision-y-reentrenamiento.md`)

| # | Item | Estado | Notas |
|---|---|---|---|
| C3 | **Watchdog de pérdida de transmisión** | ✅ HECHO | Scheduler APScheduler cada 5 min; SIN_TRANSMISION baja/media/alta; silencia por incidencia abierta; limpia al reanudar. |
| C4 | **Recalibración de θ automática (mensual)** | ✅ HECHO (2026-07-04) | `theta_service` recalibra θ = P95(recon_error normal) desde `health_readings`; conserva θ_train; guarda de mínimo de lecturas; invalida el cache del registry (θ nuevo sin reiniciar); endpoint `/recalibrate-theta`; job mensual en scheduler (`THETA_RECAL_ENABLED`). Tests en `test_theta_service.py` (9). Verificado E2E. |
| C5 | **Reentrenamiento completo del ensemble** | ✅ HECHO (2026-07-04) | `retrain_service.should_retrain` aplica los criterios de degradación (spec §2.3) desde `model_metrics` + θ drift; endpoint diagnóstico `/should-retrain`; `retrain_station` orquesta (opt-in `RETRAIN_ENABLED`, delega al pipeline batch, invalida cache); chequeo diario en scheduler (`RETRAIN_CHECK_ENABLED`). El entrenamiento pesado reusa el pipeline existente. Tests en `test_retrain_service.py` (11). Verificado E2E. |
| C6 | **Métricas de monitoreo del modelo persistidas** | ✅ HECHO (2026-07-04) | Tabla `model_metrics` (migración ml_005); `metrics_service` agrega `health_readings` por estación/ventana (tasa de alerta, θ vigente); endpoints `/metrics` + `/run-metrics`; job diario en el scheduler (`METRICS_ENABLED`). Tests en `test_metrics_service.py` (7). Verificado E2E. |

### Regla de consolidación de alertas (`docs/regla-consolidacion-alertas.md`)

| # | Item | Estado | Notas |
|---|---|---|---|
| C7 | **Consolidación de alertas → incidencias** | ✅ HECHO | Ventana 24h, umbrales 5/3/1, dedup por equipo, escalada de prioridad, `origen=monitor_salud`. |

### Onboarding y operación (`docs/runbook-onboarding-estacion.md`)

| # | Item | Estado | Notas |
|---|---|---|---|
| C8 | **Onboarding automatizado de estación nueva** | ❌ Pendiente | Hoy 100% manual (correr scripts). Flujo auto: detectar → warm-up → entrenar → activar θ. Requiere scheduler (ya existe). |
| C9 | **Silenciamiento por mantenimiento (ventana explícita)** | ✅ HECHO (2026-07-05) | Ventana de mantenimiento DERIVADA del estado ITIL (sin flag persistido): arranca al asignar técnico (correctiva `pendiente`→`en_ejecucion`) y termina al cerrar (`finalizado`/`cancelado`). Durante la ventana la regla de consolidación hace **noop total** (ni crea ni escala; acción `maintenance`) — las anomalías durante la intervención son esperadas. Sólo `en_ejecucion` silencia: `pendiente` aún escala urgencia, `resuelto` no enmascara reincidencias. Choke point único `create_or_escalate_monitor_incidencia` (`_device_in_maintenance_window`), sin llamada cross-service (estado local de ops), fail-safe. Tests ops `TestC9VentanaMantenimiento` (C9-01..04). Ver `regla-consolidacion-alertas.md §C9`. |
| C10 | **Validación de escala de sensores en ingesta** | ✅ HECHO (2026-07-05) | `ensemble_notify_service` valida que las 4 features caigan en el rango físico de la escala OEFA (`OEFA_RANGES`; discriminadores claros: flow>10 o lamp>300 = escala Thermo). Fuera de rango → `valido=0` → gate §3.0 → SIN_DATOS (fallback seguro), evitando el `recon_error`~1e9. NO convierte unidades (no se conoce la fórmula); rechaza limpiamente. Verificado E2E: lectura Thermo → SIN_DATOS; lectura OEFA → SANO normal. Tests: iot `test_ensemble_notify.py` (rechazo Thermo, aceptación OEFA, frontera, parcial, E2E) + ml `test_health_service.py` (defensa en profundidad: el ensemble sigue robusto). Ver `memory/project_c1_scale_bug.md`. |

---

## 🟡 Gestión de Incidencias ITIL v4 (`docs/spec-racionalizacion-dashboard-e-incidencias.md` §4)

| # | Item | Estado | Notas |
|---|---|---|---|
| I1 | **Modelo de Incidente ITIL** | ✅ HECHO backend (2026-07-05) | Categoría, impacto×urgencia→prioridad (matriz 3×3), sub-estado `resuelto`, timestamps SLA. `equipos.criticidad`=impacto (migr iot 005), campos ITIL en incidencias (migr ops_007). |
| I2 | **Gestión de Problemas** | ✅ HECHO backend | Tabla `problemas` (migr ops_006) + `incidencias.problema_id`; CRUD + vincular; endpoints via gateway. |
| I3 | **Ciclo de vida ITIL** | ✅ HECHO backend | pendiente→en_ejecucion→resuelto→finalizado/cancelado con transiciones validadas (400 si inválida). **Auto-cierre por el ensemble**: resuelto + N SANO → finalizado (calibración); +48h sin datos → cancelado. `resuelto`=abierto en dedup+watchdog. |
| I4 | **SLA y tiempos** | ✅ HECHO backend | `fecha_asignacion/resolucion/cierre` sellados en cada transición. |
| I5 | **Frontend ITIL** | ✅ HECHO (2026-07-05) | Detalle de incidencia con impacto/urgencia/categoría + timeline SLA + dropdown de estado con solo transiciones válidas + vincular a Problema + botón "Ver Problema". Vista de Problemas (lista + detalle con incidentes vinculados). Criticidad editable en detalle de equipo. Nav "Problemas" + RouteGuard. typecheck 0, e2e 40 verde, verificado en navegador. |

---

## 🟢 Mejoras del monitor de salud (menor prioridad)

| # | Item | Notas |
|---|---|---|
| M1 | **6.ª feature multi-gas** | Incorporar H2S/CO o columnas extra al ensemble. |
| M2 | **θ adaptativo continuo** | Ventana móvil en vez de recalibración periódica. |
| M3 | **Panel detalle de los 2 detectores** | ✅ HECHO (2026-07-05). Por lectura: AE (error vs θ) · IF (anómalo) · AND → estado (poc-dashboard §3.2). Datos ya persistidos (`health_readings`: `recon_error`, `theta`, `if_anomaly`, `and_alert`, `severity`; el veredicto AE se deriva como `recon_error > theta`) — sin migración. Backend: `if_anomaly`+`severity` añadidos a `HealthReadingPoint` schema + endpoint `/readings`. Frontend: `DetectorBreakdownPanel` en tab Salud + tooltip enriquecido en `ReconErrorChart`. Tests: ml `test_m3_readings_*` (2), e2e breakdown panel. |
| M4 | **Reincorporar CA-CHILLO-01** | Excluida por varianza colapsada; reincorporar con datos de régimen estable. |

---

## Infraestructura y Despliegue
1. **Despliegue AWS** - Lambda + API Gateway + RDS + S3 + CloudWatch
2. **Preview deploys** - Vercel previews automaticos por PR
3. **Service mesh** - Service discovery y circuit breakers entre microservicios
4. **Monitoring distribuido** - Tracing con OpenTelemetry entre servicios

## Autenticacion y Seguridad
5. **Amazon Cognito** - Migrar de JWT propio a Cognito
6. **Rate limiting** - Proteccion contra abuso en endpoints IoT
7. **API versioning avanzado** - Versionado independiente por microservicio

## Funcionalidades
8. **Exportacion reportes** - PDF (WeasyPrint) y Excel (openpyxl)
9. **Adjuntar evidencias** - Upload de archivos en calibraciones (S3 + presigned URLs)
10. **Notificaciones** - Email (SES) y/o push al crear incidencia
11. **Calibraciones avanzadas** - Alertas de vencimiento proximo, workflow de aprobacion
12. **Archivos evidencia** - Tabla archivos_evidencia con gestion documental

## Integraciones
13. **IoT real** - Integracion Campbell CR310 via HTTP/MQTT (relacionado con C1)
14. **Monitoreo** - CloudWatch dashboards, alarmas, metricas custom
15. **Websockets** - Actualizacion en tiempo real del dashboard (hoy polling 30s)

## Calidad
16. **Tests E2E** - Playwright para flujos criticos (parcial: hay specs e2e)
17. **Internacionalizacion** - Soporte multiidioma
