# Especificación Técnica de la Solución

## 1. Nombre del proyecto

**Sistema predictivo para reducir las fallas de los equipos de medición directa para la calidad de aire basado en Machine Learning e IoT en laboratorios de ensayos del Perú**

---

## 2. Resumen ejecutivo

La solución propone una plataforma web y backend serverless orientada al monitoreo predictivo de equipos de medición directa de calidad de aire usados por laboratorios de ensayo, tomando como caso de estudio el laboratorio de la OEFA. El sistema integra:

- Captura IoT de lecturas operativas desde dataloggers Campbell CR310.
- Almacenamiento histórico y trazable en la nube.
- Procesamiento y normalización de datos.
- Ejecución de modelos de Machine Learning para estimar probabilidad de falla y vida útil remanente.
- Gestión de alertas e incidencias.
- Seguimiento de calibraciones y mantenimiento.
- Dashboards operativos y reportes de auditoría alineados con ISO/IEC 17025:2017.

El objetivo es pasar de un esquema reactivo a uno predictivo, reduciendo paradas no planificadas, fortaleciendo la confiabilidad de resultados y mejorando la trazabilidad operativa.

---

## 3. Contexto del problema

Los laboratorios de ensayo que monitorean calidad de aire requieren que sus equipos operen de manera continua, confiable y con trazabilidad. En el caso de OEFA, el incremento de fallas técnicas en equipos de medición directa genera:

- Riesgo de interrupción operativa.
- Afectación en la validez de los resultados.
- Dificultad para demostrar trazabilidad ante auditorías.
- Incumplimiento potencial de requisitos de la ISO/IEC 17025:2017.
- Ausencia de herramientas tecnológicas especializadas para anticipar fallas.

La solución busca cerrar esa brecha mediante un sistema que combine **IoT + analítica + predicción + gestión operativa**.

---

## 4. Objetivos del sistema

### 4.1 Objetivo general

Desarrollar un sistema predictivo para reducir las fallas de los equipos de medición directa para la calidad de aire basado en Machine Learning e IoT, a fin de mejorar la fiabilidad operativa de los equipos en el monitoreo ambiental.

### 4.2 Objetivos específicos

| ID   | Descripción                                                              |
|------|--------------------------------------------------------------------------|
| OE01 | Analizar y seleccionar algoritmos y herramientas para monitoreo predictivo. |
| OE02 | Diseñar un sistema predictivo con Random Forest e IoT.                   |
| OE03 | Desarrollar el sistema predictivo.                                       |
| OE04 | Validar la precisión del sistema propuesto.                              |

---

## 5. Alcance funcional

El sistema cubrirá los siguientes dominios:

1. Ingesta de lecturas IoT desde equipos/dataloggers.
2. Validación, limpieza y normalización de datos.
3. Persistencia histórica de telemetría y bitácoras.
4. Ejecución de modelo ML preentrenado.
5. Registro de predicciones por equipo.
6. Generación de alertas e incidencias.
7. Gestión de equipos, calibraciones y acciones correctivas.
8. Dashboard en tiempo real y panel de KPIs.
9. Reportes mensuales de auditoría.
10. Control de acceso por roles.

---

## 6. Arquitectura de solución

### 6.1 Vista de alto nivel

La arquitectura propuesta sigue un enfoque de **microservicios ligeros / servicios desacoplados**, con frontend web, backend API, pipeline de datos y módulo de predicción.

#### Flujo general

1. Los equipos de monitoreo capturan variables operativas.
2. El datalogger CR310 transmite datos a la nube.
3. Un backend API recibe, valida y almacena las lecturas.
4. Un servicio de preprocesamiento transforma los datos al formato requerido por el modelo.
5. Un servicio ML carga el modelo preentrenado desde S3 y genera predicciones.
6. Las predicciones se almacenan y son evaluadas por reglas de negocio.
7. Si se detecta riesgo, se generan alertas, incidencias y notificaciones.
8. El frontend expone dashboards, trazabilidad, calibraciones, incidencias y reportes.

### 6.2 Componentes principales

#### C1. Capa IoT / Adquisición de datos

Responsable de capturar datos operativos de los equipos y transmitirlos cada 5 minutos.

**Entradas típicas:**

- Corriente
- Humedad
- Temperatura
- Intensidad de lámpara UV
- Flujo de muestra
- Gases medidos según analizador

**Tecnología base:**

- Campbell CR310
- Protocolo HTTP o MQTT
- Payload JSON

#### C2. API de ingestión

Servicio backend encargado de recibir las lecturas enviadas por el datalogger.

**Responsabilidades:**

- Autenticar origen si aplica.
- Validar estructura JSON.
- Registrar timestamp de recepción.
- Almacenar lectura cruda.
- Devolver respuesta HTTP `200` / `400` / `500`.

**Tecnologías sugeridas:** FastAPI, AWS Lambda, API Gateway, CloudWatch.

#### C3. Servicio de procesamiento de datos

Módulo encargado de transformar datos crudos a un formato estandarizado para persistencia analítica y consumo del modelo.

**Responsabilidades:**

- Casting numérico.
- Eliminación o marcación de nulos.
- Detección de inconsistencias.
- Normalización.
- Construcción de features.

#### C4. Servicio de predicción ML

Servicio que ejecuta el modelo preentrenado de Random Forest / RUL.

**Responsabilidades:**

- Cargar artefactos del modelo desde S3.
- Cargar metadata de features.
- Alinear el input con el formato esperado.
- Calcular probabilidad de falla.
- Estimar vida útil remanente.
- Devolver salida versionada.

#### C5. Motor de reglas de negocio

Módulo que interpreta la predicción y dispara eventos operativos.

**Reglas iniciales:**

| Condición                                        | Acción                    |
|--------------------------------------------------|---------------------------|
| `rul_dias <= 30`                                 | Generar alerta            |
| Equipo con >= 2 alertas altas en 1 día           | Generar incidencia        |
| Incidencia creada                                | Cambiar estado a `en_revision` |
| Incidencia creada                                | Notificar al coordinador  |

#### C6. Gestión operativa y trazabilidad

Módulo de negocio para mantenimiento, incidencias, calibraciones y acciones correctivas.

**Responsabilidades:**

- CRUD de equipos.
- Gestión de incidencias.
- Seguimiento de calibraciones.
- Evidencias y certificados.
- Historial de cambios.
- Auditoría.

#### C7. Frontend web

Aplicación para usuarios administrativos y técnicos.

**Módulos:**

- Login
- Dashboard tiempo real
- Panel de equipos
- Alertas
- Incidencias
- Calibraciones
- Reportes
- Administración de usuarios/roles

**Tecnologías sugeridas:** React + Next.js + TypeScript + TailwindCSS.

---

## 7. Arquitectura lógica

### 7.1 Frontend

| Aspecto        | Detalle                              |
|----------------|--------------------------------------|
| **Lenguaje**   | TypeScript                           |
| **Framework**  | React + Next.js                      |
| **Estilos**    | TailwindCSS                          |
| **Testing**    | Jest + React Testing Library         |
| **Linting**    | ESLint + Prettier                    |

**Responsabilidades:**

- Renderizar paneles y formularios.
- Consumir APIs REST.
- Mostrar estado operativo.
- Filtrar y exportar reportes.
- Administrar vistas por rol.

### 7.2 Backend

| Aspecto        | Detalle                              |
|----------------|--------------------------------------|
| **Lenguaje**   | Python 3.x                           |
| **Framework**  | FastAPI                              |
| **Testing**    | Pytest                               |
| **Linting**    | Flake8                               |
| **Infra**      | AWS Lambda + API Gateway + CloudWatch |

**Responsabilidades:**

- Exponer APIs REST.
- Orquestar lógica de negocio.
- Integrar servicios de persistencia.
- Invocar predicción.
- Manejar seguridad y auditoría.

### 7.3 Machine Learning

| Aspecto          | Detalle                                  |
|------------------|------------------------------------------|
| **Lenguaje**     | Python                                   |
| **Librerías**    | pandas, numpy, scikit-learn, joblib      |
| **Entrenamiento**| Google Colab / SageMaker Free Tier       |
| **Artefactos**   | S3 para versionado                       |

**Responsabilidades:**

- Entrenamiento offline.
- Serialización del modelo.
- Versionado.
- Inferencia periódica.
- Evaluación de desempeño.

### 7.4 Persistencia

**Sugerencia de almacenamiento híbrido:**

| Componente       | Uso                                              |
|------------------|--------------------------------------------------|
| **RDS PostgreSQL** | Datos transaccionales y trazabilidad           |
| **S3**           | Datasets, modelos, reportes y evidencias         |

**Justificación:**

- RDS soporta relaciones, consultas, auditoría y consistencia.
- S3 permite almacenar artefactos pesados y evidencia documental.

---

## 8. Arquitectura física en AWS

### Servicios propuestos

| Servicio              | Función                                        |
|-----------------------|------------------------------------------------|
| API Gateway           | Exposición segura de endpoints                 |
| AWS Lambda            | Ejecución serverless del backend y reglas      |
| Amazon RDS (PostgreSQL) | Base relacional principal                    |
| Amazon S3             | Modelos, datasets, reportes, certificados      |
| CloudWatch            | Logs, monitoreo y alertas técnicas             |
| GitHub Actions        | CI/CD                                          |
| Vercel                | Despliegue frontend                            |
| Cognito o JWT propio  | Autenticación                                  |

### Distribución recomendada

- **Frontend** desplegado en Vercel.
- **Backend API** desplegado en Lambda + API Gateway.
- **Predicción** como Lambda separada o servicio FastAPI dedicado.
- **Base de datos** en RDS PostgreSQL.
- **Archivos** en S3.

---

## 9. Diseño de módulos

### 9.1 Módulo de ingestión IoT

**Funciones:** registrar telemetría, validar payload, persistir lectura, devolver acuse.

**Endpoint sugerido:** `POST /api/v1/iot/readings`

**Request ejemplo:**

```json
{
  "deviceId": "EQ-CR310-001",
  "equipment": "Analizador SO2",
  "timestamp": "2026-03-14T10:00:00Z",
  "SO2_ppb": 12.5,
  "UVLampIntensity": 85.2,
  "SampleFlow": 1.45,
  "Box_Temp": 28.6,
  "humidity": 63.5,
  "current": 4.1
}
```

**Response exitosa:**

```json
{
  "message": "Lectura registrada correctamente",
  "deviceId": "EQ-CR310-001",
  "status": "ok"
}
```

### 9.2 Módulo de preprocesamiento

**Funciones:** convertir tipos, limpiar datos, validar rangos, normalizar formato, construir vector de features.

**Reglas técnicas iniciales:**

- Timestamps en UTC.
- Decimales normalizados.
- Descarte o marca de lecturas incompletas.
- Mapeo consistente por `deviceId`.

### 9.3 Módulo de predicción

**Funciones:** cargar modelo desde S3, cargar lista de features esperadas, transformar input, calcular:

- Probabilidad de falla.
- RUL en días.
- Nivel de riesgo.

**Salida esperada:**

```json
{
  "deviceId": "EQ-CR310-001",
  "predictionTimestamp": "2026-03-14T11:00:00Z",
  "modelVersion": "rf-rul-v1.0.0",
  "failureProbability": 0.82,
  "remainingUsefulLifeDays": 24,
  "riskLevel": "high"
}
```

### 9.4 Módulo de alertas

**Reglas:**

| RUL (días)  | Nivel            |
|-------------|------------------|
| <= 30       | Alerta alta      |
| 31 a 60     | Alerta media     |
| > 60        | Monitoreo normal |

**Endpoints sugeridos:**

- `GET /api/v1/alerts`
- `POST /api/v1/alerts/evaluate`

### 9.5 Módulo de incidencias

**Reglas:** 2 o más alertas altas del mismo equipo en un día generan incidencia automática.

**Estados:** `pendiente` → `en_proceso` → `resuelta`

**Campos mínimos:**

| Campo        | Descripción                     |
|--------------|---------------------------------|
| `id`         | Identificador único             |
| `deviceId`   | Equipo asociado                 |
| `fecha`      | Fecha del incidente             |
| `descripcion`| Detalle del incidente           |
| `responsable`| Usuario asignado                |
| `estado`     | Estado actual                   |
| `prioridad`  | Nivel de prioridad              |

### 9.6 Módulo de calibraciones

**Funciones:** registrar calibración, adjuntar evidencia, consultar vigencia, alertar vencimiento próximo.

**Archivos:** certificados PDF, constancias, evidencias fotográficas.

### 9.7 Módulo de dashboard

**Vistas:**

- Salud general de equipos.
- Lecturas en tiempo real.
- Últimas predicciones.
- Equipos críticos.
- Incidencias activas.
- Calibraciones por vencer.
- Tendencia histórica.

### 9.8 Módulo de auditoría

**Funciones:** consolidar mantenimiento, trazabilidad de acciones, exportación PDF/Excel, almacenamiento histórico automático.

---

## 10. Modelo de datos conceptual

### 10.1 Entidades principales

- `usuarios`
- `roles`
- `equipos`
- `lecturas_iot`
- `predicciones`
- `alertas`
- `incidencias`
- `acciones_correctivas`
- `calibraciones`
- `archivos_evidencia`
- `auditoria_eventos`

### 10.2 Relación principal

```
equipos ──1:N──> lecturas_iot
equipos ──1:N──> predicciones
predicciones ──1:1──> alertas
alertas ──N:1──> incidencias
incidencias ──1:N──> acciones_correctivas
equipos ──1:N──> calibraciones
* ──────────────> auditoria_eventos
```

### 10.3 Tablas sugeridas

#### `equipos`

| Campo               | Tipo       |
|---------------------|------------|
| `id`                | PK         |
| `device_id`         | VARCHAR    |
| `nombre`            | VARCHAR    |
| `tipo`              | VARCHAR    |
| `ubicacion`         | VARCHAR    |
| `estado`            | VARCHAR    |
| `fecha_registro`    | TIMESTAMP  |
| `fecha_actualizacion` | TIMESTAMP |

#### `lecturas_iot`

| Campo               | Tipo       |
|---------------------|------------|
| `id`                | PK         |
| `device_id`         | FK         |
| `timestamp_lectura` | TIMESTAMP  |
| `corriente`         | DECIMAL    |
| `humedad`           | DECIMAL    |
| `temperatura`       | DECIMAL    |
| `so2_ppb`           | DECIMAL    |
| `uv_lamp_intensity` | DECIMAL    |
| `sample_flow`       | DECIMAL    |
| `raw_payload`       | JSONB      |
| `created_at`        | TIMESTAMP  |

#### `predicciones`

| Campo                        | Tipo       |
|------------------------------|------------|
| `id`                         | PK         |
| `device_id`                  | FK         |
| `model_version`              | VARCHAR    |
| `prediction_timestamp`       | TIMESTAMP  |
| `failure_probability`        | DECIMAL    |
| `remaining_useful_life_days` | INTEGER    |
| `risk_level`                 | VARCHAR    |
| `feature_snapshot`           | JSONB      |
| `created_at`                 | TIMESTAMP  |

#### `alertas`

| Campo           | Tipo       |
|-----------------|------------|
| `id`            | PK         |
| `device_id`     | FK         |
| `prediccion_id` | FK         |
| `nivel_riesgo`  | VARCHAR    |
| `descripcion`   | TEXT       |
| `estado`        | VARCHAR    |
| `created_at`    | TIMESTAMP  |

#### `incidencias`

| Campo            | Tipo       |
|------------------|------------|
| `id`             | PK         |
| `device_id`      | FK         |
| `fecha_incidente`| TIMESTAMP  |
| `descripcion`    | TEXT       |
| `responsable_id` | FK         |
| `estado`         | VARCHAR    |
| `prioridad`      | VARCHAR    |
| `created_at`     | TIMESTAMP  |
| `updated_at`     | TIMESTAMP  |

#### `acciones_correctivas`

| Campo            | Tipo       |
|------------------|------------|
| `id`             | PK         |
| `incidencia_id`  | FK         |
| `responsable_id` | FK         |
| `descripcion`    | TEXT       |
| `observaciones`  | TEXT       |
| `fecha_accion`   | TIMESTAMP  |

#### `calibraciones`

| Campo                 | Tipo       |
|-----------------------|------------|
| `id`                  | PK         |
| `device_id`           | FK         |
| `fecha_calibracion`   | TIMESTAMP  |
| `fecha_vencimiento`   | TIMESTAMP  |
| `tecnico_responsable` | VARCHAR    |
| `evidencia_url`       | VARCHAR    |
| `observaciones`       | TEXT       |

#### `usuarios`

| Campo                       | Tipo       |
|-----------------------------|------------|
| `id`                        | PK         |
| `nombre`                    | VARCHAR    |
| `correo`                    | VARCHAR    |
| `password_hash` o `cognito_sub` | VARCHAR |
| `rol_id`                    | FK         |
| `estado`                    | VARCHAR    |

#### `roles`

| Campo        | Tipo       |
|--------------|------------|
| `id`         | PK         |
| `nombre`     | VARCHAR    |
| `descripcion`| TEXT       |

#### `auditoria_eventos`

| Campo        | Tipo       |
|--------------|------------|
| `id`         | PK         |
| `entidad`    | VARCHAR    |
| `entidad_id` | INTEGER    |
| `accion`     | VARCHAR    |
| `usuario_id` | FK         |
| `detalle`    | JSONB      |
| `timestamp`  | TIMESTAMP  |

---

## 11. APIs propuestas

### 11.1 Autenticación

| Método | Endpoint                  |
|--------|---------------------------|
| POST   | `/api/v1/auth/login`      |
| POST   | `/api/v1/auth/refresh`    |
| POST   | `/api/v1/auth/logout`     |

### 11.2 Equipos

| Método | Endpoint                          |
|--------|-----------------------------------|
| GET    | `/api/v1/equipments`              |
| POST   | `/api/v1/equipments`              |
| GET    | `/api/v1/equipments/{deviceId}`   |
| PUT    | `/api/v1/equipments/{deviceId}`   |
| DELETE | `/api/v1/equipments/{deviceId}`   |

### 11.3 Lecturas IoT

| Método | Endpoint                                  |
|--------|-------------------------------------------|
| POST   | `/api/v1/iot/readings`                    |
| GET    | `/api/v1/iot/readings/{deviceId}`         |
| GET    | `/api/v1/iot/readings/{deviceId}/latest`  |

### 11.4 Predicciones

| Método | Endpoint                                    |
|--------|---------------------------------------------|
| POST   | `/api/v1/predictions/run`                   |
| GET    | `/api/v1/predictions/{deviceId}`            |
| GET    | `/api/v1/predictions/{deviceId}/latest`     |

### 11.5 Alertas

| Método | Endpoint                        |
|--------|---------------------------------|
| GET    | `/api/v1/alerts`                |
| GET    | `/api/v1/alerts/{deviceId}`     |
| POST   | `/api/v1/alerts/evaluate`       |

### 11.6 Incidencias

| Método | Endpoint                              |
|--------|---------------------------------------|
| GET    | `/api/v1/incidents`                   |
| POST   | `/api/v1/incidents`                   |
| PUT    | `/api/v1/incidents/{id}/status`       |
| POST   | `/api/v1/incidents/{id}/actions`      |

### 11.7 Calibraciones

| Método | Endpoint                                |
|--------|-----------------------------------------|
| GET    | `/api/v1/calibrations`                  |
| POST   | `/api/v1/calibrations`                  |
| GET    | `/api/v1/calibrations/{deviceId}`       |
| POST   | `/api/v1/calibrations/{id}/attachment`  |

### 11.8 Dashboard y reportes

| Método | Endpoint                            |
|--------|-------------------------------------|
| GET    | `/api/v1/dashboard/realtime`        |
| GET    | `/api/v1/dashboard/kpis`            |
| GET    | `/api/v1/reports/monthly`           |
| POST   | `/api/v1/reports/monthly/export`    |

---

## 12. Reglas de negocio

1. Toda lectura debe asociarse a un `deviceId`.
2. La API debe responder en menos de 1 segundo para la recepción IoT.
3. La ingesta debe registrar al menos 95% de las lecturas esperadas.
4. Toda predicción debe incluir `timestamp` y `modelVersion`.
5. Si RUL <= 30 días, se crea alerta.
6. Si un equipo acumula 2 alertas altas en un día, se crea incidencia.
7. La incidencia cambia el estado del equipo a `en_revision`.
8. Solo **Técnico** o **Administrador** pueden cambiar estado de incidencias.
9. Toda calibración debe quedar trazada y con evidencia adjunta.
10. Todo cambio relevante genera evento de auditoría.

---

## 13. Requerimientos no funcionales

### 13.1 Rendimiento

- Tiempo de respuesta del endpoint de ingesta: **< 1 segundo**.
- Dashboard con actualización visual menor a **10 segundos**.
- Predicciones programadas **cada 1 hora**.

### 13.2 Disponibilidad

- Backend diseñado para alta disponibilidad usando Lambda.
- Persistencia respaldada en RDS y S3.
- Reintentos y logging ante fallos de transmisión.

### 13.3 Escalabilidad

- Arquitectura serverless para absorber variaciones en volumen de telemetría.
- Separación entre ingesta, procesamiento e inferencia.

### 13.4 Seguridad

- JWT o Cognito.
- Control de acceso por roles.
- Encriptación TLS en tránsito.
- Políticas IAM mínimas necesarias.
- Registro de auditoría para acciones sensibles.

### 13.5 Trazabilidad

- Bitácoras de lecturas, predicciones, alertas, incidencias, calibraciones y acciones correctivas.
- Historial de modelo y versión usada por predicción.

### 13.6 Mantenibilidad

- Código tipado y estandarizado.
- Arquitectura por capas.
- CI/CD automatizado.
- Cobertura mínima de pruebas sugerida: **80%** en módulos críticos.

---

## 14. Diseño del modelo de Machine Learning

### 14.1 Enfoque inicial

Se propone usar **Random Forest** para estimar:

- Probabilidad de falla.
- Clasificación de riesgo.
- Vida útil remanente (RUL) mediante aproximación supervisada.

### 14.2 Variables candidatas

| Variable                    | Fuente                |
|-----------------------------|-----------------------|
| Corriente                   | Sensor / datalogger   |
| Humedad                     | Sensor / datalogger   |
| Temperatura                 | Sensor / datalogger   |
| Intensidad de lámpara UV    | Sensor / datalogger   |
| Flujo de muestra            | Sensor / datalogger   |
| Gases medidos               | Analizador            |
| Frecuencia de fallas previas| Histórico             |
| Historial de mantenimiento  | Registro operativo    |
| Antigüedad del equipo       | Registro operativo    |
| Eventos de calibración      | Registro operativo    |

### 14.3 Pipeline ML

1. Extracción de históricos.
2. Limpieza.
3. Tratamiento de nulos.
4. Ingeniería de características.
5. Entrenamiento.
6. Validación.
7. Serialización.
8. Despliegue.
9. Inferencia periódica.
10. Monitoreo del modelo.

### 14.4 Artefactos versionables

| Artefacto              | Descripción                         |
|------------------------|-------------------------------------|
| `rul_model.pkl`        | Modelo serializado                  |
| `feature_names.json`   | Lista de features esperadas         |
| `model_metadata.json`  | Metadata del modelo (versión, métricas) |

### 14.5 Métricas sugeridas

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC
- MAE / RMSE (si RUL se maneja como regresión)

---

## 15. Seguridad y control de acceso

### Roles

| Rol              | Permisos                                                                 |
|------------------|--------------------------------------------------------------------------|
| **Administrador** | Gestión total: usuarios, roles, configuración, reportes.                |
| **Técnico**       | Incidencias, acciones correctivas, calibraciones, consulta de equipos.  |
| **Coordinador**   | Dashboard, revisión de alertas, seguimiento de incidencias, reportes.   |

### Mecanismos

- Autenticación con Cognito o JWT.
- Autorización RBAC.
- Expiración de token.
- Hashing seguro de contraseñas si es local.
- Auditoría de accesos.

---

## 16. Observabilidad y monitoreo técnico

### Logs

- Recepción de lecturas.
- Errores de validación.
- Errores de inferencia.
- Eventos de negocio.
- Envío de notificaciones.

### Métricas

- Porcentaje de lecturas registradas.
- Tasa de errores de ingesta.
- Tiempo promedio de respuesta.
- Número de alertas por día.
- Número de incidencias por equipo.
- Precisión del modelo.

### Herramienta

AWS CloudWatch.

---

## 17. Estrategia de despliegue

### 17.1 Frontend

- Repositorio GitHub.
- Despliegue en Vercel.
- Branches: `dev`, `qa`, `main`.
- Previews automáticos por pull request.

### 17.2 Backend

- Empaquetado y despliegue vía GitHub Actions.
- Despliegue a Lambda.
- Configuración de API Gateway.
- Variables por ambiente.

### 17.3 Ambientes

| Ambiente      | Descripción               |
|---------------|---------------------------|
| `desarrollo`  | Desarrollo local y pruebas |
| `pruebas`     | QA y validación            |
| `producción`  | Entorno productivo         |

### 17.4 CI/CD mínimo

1. Lint
2. Unit tests
3. Build
4. Deploy condicionado por rama

---

## 18. Trazabilidad con historias de usuario

La arquitectura cubre directamente las HUs definidas:

| Historias       | Cobertura                                      |
|-----------------|-------------------------------------------------|
| HU001 - HU004  | Ingestión, validación y preprocesamiento.       |
| HU005 - HU006  | Ejecución y registro de predicciones.           |
| HU007 - HU008  | Autenticación y control de roles.               |
| HU009 - HU010  | Gestión de equipos y trazabilidad por deviceId. |
| HU011 - HU013  | Alertas, incidencias y notificaciones.          |
| HU014 - HU016  | Operación de mantenimiento y calibraciones.     |
| HU017 - HU019  | Dashboard, KPIs y reportes de auditoría.        |

---

## 19. Priorización técnica por sprint

### Sprint 1 — Cadena de ingesta

> **Meta técnica:** dejar operativa la cadena de ingesta.

- API de recepción.
- Validación JSON.
- Almacenamiento de lecturas.
- Preprocesamiento automático.

### Sprint 2 — Predicciones y alertas

> **Meta técnica:** generar predicciones y alertas.

- Carga del modelo desde S3.
- Predicciones automáticas.
- Persistencia de resultados.
- Asociación por deviceId.
- Reglas de alerta.

### Sprint 3 — Gestión operativa

> **Meta técnica:** operacionalizar mantenimiento.

- CRUD de equipos.
- Incidencias.
- Notificaciones.
- Acciones correctivas.
- Calibraciones.
- Dashboard tiempo real.

### Sprint 4 — Gobierno y cumplimiento

> **Meta técnica:** fortalecer gobierno y cumplimiento.

- Autenticación.
- Roles.
- KPIs consolidados.
- Reportes auditables PDF/Excel.

---

## 20. Riesgos técnicos y mitigaciones

| #  | Riesgo                                            | Mitigación                                                                  |
|----|---------------------------------------------------|-----------------------------------------------------------------------------|
| 1  | Datos incompletos o corruptos                     | Validación estricta, logs, rechazo controlado, reintentos.                  |
| 2  | Baja calidad del histórico para entrenar el modelo | Pipeline de limpieza, etiquetado manual inicial, validación con expertos.  |
| 3  | Latencia o pérdida de conectividad IoT            | Buffer local en datalogger, reenvío, monitoreo de disponibilidad.           |
| 4  | Deriva del modelo                                 | Versionado, reentrenamiento planificado, monitoreo de métricas.             |
| 5  | Incumplimiento de trazabilidad                    | Auditoría transversal, evidencia adjunta, almacenamiento histórico.         |

---

## 21. Propuesta de arquitectura final recomendada

### Recomendación principal

Implementar una arquitectura compuesta por:

| Capa                  | Tecnología                              |
|-----------------------|-----------------------------------------|
| Frontend              | Next.js + TypeScript + Tailwind         |
| Backend transaccional | FastAPI sobre Lambda + API Gateway      |
| Base principal        | PostgreSQL en RDS                       |
| Almacenamiento        | S3 (documentos y modelos)               |
| ML                    | scikit-learn con artefactos en S3       |
| Inferencias           | Lambda programada cada hora             |
| Autenticación         | Cognito o JWT                           |
| Monitoreo             | CloudWatch                              |
| CI/CD                 | GitHub Actions                          |
| Despliegue frontend   | Vercel                                  |

### Justificación

Este diseño equilibra:

- Bajo costo.
- Escalabilidad.
- Trazabilidad.
- Simplicidad de operación.
- Compatibilidad con alcance académico y funcional.
- Rápida implementación para tesis/prototipo funcional.

---

## 22. Conclusión técnica

La solución propuesta permite construir una **plataforma integral de monitoreo predictivo, mantenimiento y trazabilidad** para equipos de medición de calidad de aire, alineada con los objetivos del proyecto y con los requisitos de confiabilidad operativa e ISO/IEC 17025:2017.

Desde el punto de vista de ingeniería, la arquitectura es **viable, escalable y adecuada** para una implementación incremental por sprints.
