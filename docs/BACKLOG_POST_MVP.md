# Backlog Post-MVP

Items planificados para implementacion posterior. Actualizado 2026-07-04.

---

## 🔴 CRÍTICO — Monitor de Salud (ensemble AE+IF+AND)

Pendientes del sistema de monitoreo predictivo. Ordenados por impacto. Los ✅ ya
están implementados y verificados; se listan para dar contexto.

### Gaps que bloquean el modo producción real

| # | Item | Estado | Notas |
|---|---|---|---|
| C1 | **Ingesta IoT → dispara el ensemble** | ❌ **GAP CRÍTICO** | Hoy `iot-service` al recibir una lectura **solo la guarda**; NO llama a `/health-monitor/evaluate`. El ensemble se alimenta **solo por scripts de simulación** (`scripts/simulate_*.py`). En producción real la cadena `CR310 → iot ingest → ml evaluate → salud + incidencias` está **rota**. Ver `docs/spec-racionalizacion-dashboard-e-incidencias.md` §7. **Sin esto, el sistema no monitorea nada real.** |
| C2 | **Retiro físico total del RF** | ⚠️ Parcial | Backend RF desconectado y deprecado (no crea incidencias, endpoints `deprecated`). Falta borrar pipeline/modelo/tests RF en un PR dedicado. Ver spec-racionalizacion §3 R3. |

### Detección de transmisión y reentrenamiento (`docs/spec-transmision-y-reentrenamiento.md`)

| # | Item | Estado | Notas |
|---|---|---|---|
| C3 | **Watchdog de pérdida de transmisión** | ✅ HECHO | Scheduler APScheduler cada 5 min; SIN_TRANSMISION baja/media/alta; silencia por incidencia abierta; limpia al reanudar. |
| C4 | **Recalibración de θ automática (mensual)** | ❌ Pendiente | Script `09_recalibrate_theta.py` existe; falta engancharlo al scheduler (ya existe el scheduler). |
| C5 | **Reentrenamiento completo del ensemble** | ❌ Pendiente | Trimestral o por degradación. Depende de C6 (métricas). Jobs pesados fuera del request-path. |
| C6 | **Métricas de monitoreo del modelo persistidas** | ❌ Pendiente | Tasa de alerta / especificidad por estación en el tiempo. **Prerequisito de C5** (disparo por degradación). Hoy no se registran. |

### Regla de consolidación de alertas (`docs/regla-consolidacion-alertas.md`)

| # | Item | Estado | Notas |
|---|---|---|---|
| C7 | **Consolidación de alertas → incidencias** | ✅ HECHO | Ventana 24h, umbrales 5/3/1, dedup por equipo, escalada de prioridad, `origen=monitor_salud`. |

### Onboarding y operación (`docs/runbook-onboarding-estacion.md`)

| # | Item | Estado | Notas |
|---|---|---|---|
| C8 | **Onboarding automatizado de estación nueva** | ❌ Pendiente | Hoy 100% manual (correr scripts). Flujo auto: detectar → warm-up → entrenar → activar θ. Requiere scheduler (ya existe). |
| C9 | **Silenciamiento por mantenimiento (ventana explícita)** | ⚠️ Parcial | Hoy se silencia por incidencia abierta. Falta un modo "en mantenimiento" con ventana temporal explícita si se requiere. |

---

## 🟡 Gestión de Incidencias ITIL v4 (`docs/spec-racionalizacion-dashboard-e-incidencias.md` §4)

| # | Item | Estado | Notas |
|---|---|---|---|
| I1 | **Modelo de Incidente ITIL** | ❌ Pendiente | Categoría, impacto×urgencia→prioridad, sub-estado `resuelto`, timestamps SLA. |
| I2 | **Gestión de Problemas** | ❌ Pendiente | Tabla `problemas` + relación con incidentes recurrentes (causa raíz). |
| I3 | **Ciclo de vida ITIL** | ❌ Pendiente | Nuevo→Asignado→En progreso→Resuelto→Cerrado con transiciones válidas. |
| I4 | **SLA y tiempos** | ❌ Pendiente | Registro y objetivos de tiempo (registro→asignación→resolución→cierre). |

---

## 🟢 Mejoras del monitor de salud (menor prioridad)

| # | Item | Notas |
|---|---|---|
| M1 | **6.ª feature multi-gas** | Incorporar H2S/CO o columnas extra al ensemble. |
| M2 | **θ adaptativo continuo** | Ventana móvil en vez de recalibración periódica. |
| M3 | **Panel detalle de los 2 detectores** | Por lectura: AE dice X, IF dice Y, AND → alerta (poc-dashboard §3.2). |
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
