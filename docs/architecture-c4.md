# Air Monitoring Project - Architecture Diagrams (C4 Model)

## Level 1: System Context Diagram

Muestra el sistema completo y sus interacciones con actores externos.

```mermaid
C4Context
    title Sistema de Monitoreo Predictivo de Calidad de Aire - Contexto

    Person(admin, "Administrador", "Gestiona usuarios, configuracion general y supervision del sistema")
    Person(tecnico, "Tecnico", "Opera equipos, gestiona incidencias, mantenimientos y calibraciones")
    Person(coordinador, "Coordinador", "Consulta dashboards, reportes y estado de equipos (solo lectura)")

    System(airmon, "Plataforma Air Monitoring", "Sistema predictivo para reducir fallas de equipos de medicion de calidad de aire basado en ML e IoT. Alineado con ISO/IEC 17025:2017")

    System_Ext(cr310, "Campbell CR310 Datalogger", "Dispositivo IoT que envia lecturas de sensores cada 5 min via HTTP/MQTT (SO2, H2S, temps, flujos, UV, presion)")
    System_Ext(mailtrap, "Servidor SMTP (Mailtrap)", "Servicio de email para notificaciones de incidencias y calibraciones")
    System_Ext(s3_future, "AWS S3 (futuro)", "Almacenamiento de modelos ML, certificados y reportes")

    Rel(admin, airmon, "Administra usuarios, supervisa", "HTTPS")
    Rel(tecnico, airmon, "Gestiona equipos, incidencias, calibraciones", "HTTPS")
    Rel(coordinador, airmon, "Consulta dashboards y reportes", "HTTPS")
    Rel(cr310, airmon, "Envia lecturas IoT cada 5 min", "HTTP POST JSON")
    Rel(airmon, mailtrap, "Envia notificaciones email", "SMTP")
    Rel(airmon, s3_future, "Almacena artefactos ML y certificados", "HTTPS (futuro)")
```

---

## Level 2: Container Diagram

Muestra los contenedores (servicios desplegables) que componen el sistema.

```mermaid
C4Container
    title Air Monitoring - Diagrama de Contenedores

    Person(user, "Usuario", "Admin / Tecnico / Coordinador")
    System_Ext(cr310, "Campbell CR310", "Datalogger IoT")
    System_Ext(smtp, "SMTP Server", "Mailtrap")

    Container_Boundary(system, "Plataforma Air Monitoring") {
        Container(frontend, "Frontend Web", "Next.js 16, React 19, TailwindCSS, Recharts", "SPA con dashboards, gestion de equipos, alertas, incidencias, calibraciones. Puerto :3000")

        Container(gateway, "API Gateway", "Python 3.11, FastAPI", "Punto de entrada unico. Autenticacion JWT HS256, RBAC (3 roles), proxy reverso a microservicios. Puerto :8000")

        Container(iot, "IoT Service", "Python 3.11, FastAPI", "Ingesta de lecturas IoT, CRUD equipos, validacion JSON, preprocesamiento. Puerto :8001")

        Container(ml, "ML Service", "Python 3.11, FastAPI, scikit-learn", "Predicciones ML (Random Forest), calculo failure_probability + RUL, generacion de alertas. Puerto :8002")

        Container(ops, "Ops Service", "Python 3.11, FastAPI", "Gestion operativa: incidencias, mantenimientos correctivos, calibraciones, repuestos, proveedores, usuarios. Puerto :8003")

        ContainerDb(db, "PostgreSQL 15", "PostgreSQL", "Base de datos compartida: equipos, lecturas_iot, predicciones, alertas, incidencias, calibraciones, usuarios, etc.")

        Container(ml_artifacts, "ML Artifacts", "Filesystem / S3 (futuro)", "Modelos entrenados: rul_model.pkl, failure_model.pkl, scaler.pkl, feature_names.json")
    }

    Rel(user, frontend, "Navega dashboards y gestiona", "HTTPS :3000")
    Rel(frontend, gateway, "API calls", "HTTP REST :8000")
    Rel(cr310, gateway, "POST /api/v1/iot/readings", "HTTP JSON (ruta publica)")

    Rel(gateway, iot, "Proxy /api/v1/iot/*", "HTTP :8001")
    Rel(gateway, ml, "Proxy /api/v1/predictions/*, /api/v1/alerts/*", "HTTP :8002")
    Rel(gateway, ops, "Proxy /api/v1/incidencias/*, calibraciones/*, usuarios/*, reportes/*, etc.", "HTTP :8003")

    Rel(iot, db, "Lee/escribe equipos, lecturas_iot", "SQLAlchemy + Alembic")
    Rel(ml, db, "Lee/escribe predicciones, alertas", "SQLAlchemy + Alembic")
    Rel(ops, db, "Lee/escribe incidencias, calibraciones, usuarios, etc.", "SQLAlchemy + Alembic")
    Rel(ml, ml_artifacts, "Carga modelos al inicio", "Filesystem")
    Rel(ops, smtp, "Envia notificaciones", "SMTP :2525")
```

---

## Level 3: Component Diagram - API Gateway

```mermaid
C4Component
    title API Gateway - Componentes (Puerto :8000)

    Container_Ext(frontend, "Frontend Web", "Next.js")
    Container_Ext(iot_svc, "IoT Service", ":8001")
    Container_Ext(ml_svc, "ML Service", ":8002")
    Container_Ext(ops_svc, "Ops Service", ":8003")

    Container_Boundary(gateway, "API Gateway") {
        Component(auth_routes, "Auth Routes", "FastAPI Router", "POST /auth/login, /auth/refresh, /auth/logout, GET /auth/me")
        Component(kpi_routes, "Dashboard KPI Routes", "FastAPI Router", "GET /dashboard/kpis - Agrega datos de todos los servicios")
        Component(proxy, "Reverse Proxy", "httpx.AsyncClient", "Reenvio de requests a servicios internos con headers de auth")
        Component(jwt_handler, "JWT Handler", "python-jose HS256", "Crea y verifica access/refresh tokens")
        Component(rbac, "RBAC Middleware", "FastAPI Dependency", "Valida permisos por rol: admin, tecnico, coordinador")
        Component(password, "Password Utils", "bcrypt", "Hash y verificacion de contrasenas")
    }

    Rel(frontend, auth_routes, "Login/Refresh/Logout", "HTTP")
    Rel(frontend, proxy, "API requests", "HTTP")
    Rel(auth_routes, jwt_handler, "Genera tokens")
    Rel(auth_routes, password, "Verifica credenciales")
    Rel(auth_routes, ops_svc, "GET /usuarios/by-email/{email}", "HTTP")
    Rel(proxy, rbac, "Valida permisos antes de reenviar")
    Rel(rbac, jwt_handler, "Extrae claims del token")
    Rel(proxy, iot_svc, "Reenvio /iot/*", "HTTP")
    Rel(proxy, ml_svc, "Reenvio /predictions/*, /alerts/*", "HTTP")
    Rel(proxy, ops_svc, "Reenvio /incidencias/*, /calibraciones/*, etc.", "HTTP")
    Rel(kpi_routes, iot_svc, "Fetch equipos count", "HTTP")
    Rel(kpi_routes, ml_svc, "Fetch alertas stats", "HTTP")
    Rel(kpi_routes, ops_svc, "Fetch incidencias/calibraciones stats", "HTTP")
```

---

## Level 3: Component Diagram - IoT Service

```mermaid
C4Component
    title IoT Service - Componentes (Puerto :8001)

    Container_Ext(gateway, "API Gateway", ":8000")
    Container_Ext(cr310, "CR310 Datalogger", "IoT Device")
    ContainerDb_Ext(db, "PostgreSQL", "equipos, lecturas_iot")

    Container_Boundary(iot, "IoT Service") {
        Component(equipo_routes, "Equipo Routes", "FastAPI Router", "GET/POST/PUT/DELETE /iot/equipos, /iot/equipos/{deviceId}")
        Component(reading_routes, "Reading Routes", "FastAPI Router", "POST /iot/readings, GET /iot/readings/{deviceId}, GET .../latest")
        Component(equipo_service, "Equipo Service", "Python", "Logica de negocio: CRUD equipos, validacion, soft-delete")
        Component(reading_service, "Reading Service", "Python", "Logica de ingesta: validacion JSON, mapeo device_id, almacenamiento crudo")
        Component(models, "ORM Models", "SQLAlchemy", "Equipo (15 campos expandidos), LecturaIoT (13 sensores + raw_payload)")
        Component(migrations, "Migrations", "Alembic", "001: create tables, 002: expand equipos, 003: fecha_ingreso fix")
    }

    Rel(gateway, equipo_routes, "CRUD equipos", "HTTP")
    Rel(cr310, reading_routes, "POST lecturas cada 5 min", "HTTP JSON")
    Rel(equipo_routes, equipo_service, "Delega logica")
    Rel(reading_routes, reading_service, "Delega ingesta")
    Rel(equipo_service, models, "ORM queries")
    Rel(reading_service, models, "ORM queries")
    Rel(models, db, "Read/Write", "SQLAlchemy")
    Rel(migrations, db, "Schema management", "Alembic")
```

---

## Level 3: Component Diagram - ML Service

```mermaid
C4Component
    title ML Service - Componentes (Puerto :8002)

    Container_Ext(gateway, "API Gateway", ":8000")
    ContainerDb_Ext(db, "PostgreSQL", "predicciones, alertas")
    Container_Ext(artifacts, "ML Artifacts", "rul_model.pkl, failure_model.pkl, scaler.pkl")

    Container_Boundary(ml, "ML Service") {
        Component(pred_routes, "Prediction Routes", "FastAPI Router", "POST /predictions/run, GET /predictions/{deviceId}, GET .../latest")
        Component(alert_routes, "Alert Routes", "FastAPI Router", "GET /alerts, GET /alerts/{deviceId}, PATCH /alerts/deactivate/{deviceId}")
        Component(model_manager, "Model Manager", "Python + joblib", "Carga modelos RF al startup, gestiona inferencia")
        Component(feature_eng, "Feature Engineering", "pandas + numpy", "12 sensores x 3 ventanas (1h,6h,24h) x 3 stats = 122 features")
        Component(prediction_service, "Prediction Service", "Python", "Pipeline: features -> scale -> predict RUL + failure_prob -> risk_level")
        Component(alert_service, "Alert Service", "Python", "Genera alertas segun reglas: RUL<=30 alta, 31-60 media, >60 baja")
        Component(models, "ORM Models", "SQLAlchemy", "Prediccion (failure_prob, RUL, risk_level), Alerta (nivel_riesgo, estado)")
    }

    Rel(gateway, pred_routes, "Run/Query predictions", "HTTP")
    Rel(gateway, alert_routes, "Query/Manage alerts", "HTTP")
    Rel(pred_routes, prediction_service, "Ejecuta prediccion")
    Rel(prediction_service, feature_eng, "Extrae 122 features de lecturas")
    Rel(prediction_service, model_manager, "Infiere RUL + failure_prob")
    Rel(prediction_service, alert_service, "Evalua reglas de alerta")
    Rel(model_manager, artifacts, "Carga al startup", "joblib.load()")
    Rel(alert_routes, alert_service, "Consulta/desactiva alertas")
    Rel(prediction_service, models, "Persiste predicciones")
    Rel(alert_service, models, "Persiste alertas")
    Rel(models, db, "Read/Write", "SQLAlchemy")
```

---

## Level 3: Component Diagram - Ops Service

```mermaid
C4Component
    title Ops Service - Componentes (Puerto :8003)

    Container_Ext(gateway, "API Gateway", ":8000")
    Container_Ext(smtp, "SMTP Server", "Mailtrap")
    ContainerDb_Ext(db, "PostgreSQL", "9 tablas operativas")

    Container_Boundary(ops, "Ops Service") {
        Component(incidencia_routes, "Incidencia Routes", "FastAPI Router", "CRUD incidencias, POST /evaluar, POST /{id}/mantenimiento")
        Component(calibracion_routes, "Calibracion Routes", "FastAPI Router", "CRUD calibraciones con certificado y proveedor")
        Component(usuario_routes, "Usuario Routes", "FastAPI Router", "GET/POST usuarios, GET /by-email/{email}")
        Component(catalog_routes, "Catalog Routes", "FastAPI Router", "GET dataloggers, repuestos, proveedores")
        Component(reporte_routes, "Reporte Routes", "FastAPI Router", "GET /reportes/preview, /reportes/csv, /reportes/pdf (admin+coordinador)")

        Component(incidencia_service, "Incidencia Service", "Python", "Auto-reglas: >=2 alertas altas/dia -> correctiva; finalizada -> calibracion")
        Component(notification_service, "Notification Service", "Python + smtplib", "Envia emails por nuevas incidencias y cambios de estado")
        Component(reporte_service, "Reporte Service", "Python", "Agrega datos de mantenimiento + calibracion por periodo/device_id")
        Component(export_service, "Export Service", "Python + csv/reportlab", "Genera archivos CSV y PDF de reportes de mantenimiento")
        Component(models, "ORM Models", "SQLAlchemy", "Incidencia, MantenimientoCorrectivo, Calibracion, Repuesto, Proveedor, Usuario, etc.")
        Component(migrations, "Migrations", "Alembic", "ops_001: schema + seeds, ops_002: password_hash")
    }

    Rel(gateway, incidencia_routes, "Gestion incidencias", "HTTP")
    Rel(gateway, calibracion_routes, "Gestion calibraciones", "HTTP")
    Rel(gateway, usuario_routes, "Gestion usuarios + auth lookup", "HTTP")
    Rel(gateway, catalog_routes, "Consulta catalogos", "HTTP")
    Rel(gateway, reporte_routes, "Exporta reportes (admin+coordinador)", "HTTP")
    Rel(incidencia_routes, incidencia_service, "Logica de negocio + auto-reglas")
    Rel(incidencia_service, notification_service, "Notifica cambios")
    Rel(notification_service, smtp, "Envia emails", "SMTP :2525")
    Rel(reporte_routes, reporte_service, "Consulta datos agregados")
    Rel(reporte_routes, export_service, "Genera CSV / PDF")
    Rel(reporte_service, models, "ORM queries")
    Rel(incidencia_service, models, "ORM queries")
    Rel(calibracion_routes, models, "ORM queries")
    Rel(usuario_routes, models, "ORM queries")
    Rel(models, db, "Read/Write", "SQLAlchemy")
    Rel(migrations, db, "Schema + seed data", "Alembic")
```

---

## Level 3: Component Diagram - Frontend

```mermaid
C4Component
    title Frontend Web - Componentes (Puerto :3000)

    Person_Ext(user, "Usuario")
    Container_Ext(gateway, "API Gateway", ":8000")

    Container_Boundary(frontend, "Frontend Next.js") {
        Component(auth_provider, "AuthProvider", "React Context", "Gestiona JWT tokens, auto-refresh, redirect a /login en 401")
        Component(route_guard, "RouteGuard", "React Component", "RBAC en cliente: redirige por rol (admin->dashboard, tecnico->dashboard-tecnico, coordinador->dashboard)")
        Component(login_page, "Login Page", "Next.js Page", "/login - Formulario email/password")
        Component(dashboard_page, "Dashboard Page", "Next.js Page", "/dashboard - Layout con 8 widgets + HealthSemaforo, polling cada 30s (admin+coordinador)")
        Component(dashboard_tecnico, "Dashboard Tecnico", "Next.js Page", "/dashboard-tecnico - KPIs de incidencias pendientes, repuestos disponibles (solo tecnico)")
        Component(equipo_detail, "Equipo Detail", "Next.js Page", "/equipos/[deviceId] - Vista 360° con tabs")
        Component(crud_pages, "CRUD Pages", "Next.js Pages", "/incidencias, /calibraciones, /alertas, /predicciones, /lecturas, /repuestos, /proveedores, /usuarios")
        Component(reportes_page, "Reportes Page", "Next.js Page", "/reportes - Preview/exporta CSV+PDF de mantenimiento (admin+coordinador)")

        Component(kpi_cards, "KpiCards", "React + TailwindCSS", "4 metricas: Equipos, Alertas Altas, RUL Promedio, Predicciones")
        Component(health_semaforo, "HealthSemaforo", "React + TailwindCSS", "Indicador visual de salud global del sistema por nivel de riesgo")
        Component(charts, "Chart Components", "Recharts (dynamic import)", "PredictionTrends, SensorTrends, RiskDistribution (Pie)")
        Component(data_widgets, "Data Widgets", "React + TailwindCSS", "EquipoGrid, RecentAlerts, IncidenciasSummary, ProximasCalibraciones")

        Component(api_client, "API Client", "fetch + interceptors", "Agrega Bearer token, maneja 401, routing a gateway")
        Component(api_functions, "API Functions", "TypeScript modules", "dashboard.ts, auth.ts, predicciones.ts, ops.ts, lecturas.ts")
    }

    Rel(user, login_page, "Ingresa credenciales")
    Rel(user, dashboard_page, "Visualiza metricas y estado (admin/coordinador)")
    Rel(user, dashboard_tecnico, "Visualiza incidencias y repuestos (tecnico)")
    Rel(user, equipo_detail, "Inspecciona equipo individual")
    Rel(user, crud_pages, "Gestiona entidades operativas")
    Rel(user, reportes_page, "Exporta reportes (admin/coordinador)")

    Rel(login_page, auth_provider, "Almacena tokens")
    Rel(auth_provider, route_guard, "Provee rol y estado auth")
    Rel(route_guard, dashboard_page, "Redirige admin/coordinador")
    Rel(route_guard, dashboard_tecnico, "Redirige tecnico")
    Rel(dashboard_page, kpi_cards, "Renderiza KPIs")
    Rel(dashboard_page, health_semaforo, "Renderiza estado de salud")
    Rel(dashboard_page, charts, "Renderiza graficos")
    Rel(dashboard_page, data_widgets, "Renderiza grids y tablas")
    Rel(equipo_detail, charts, "Charts por equipo")

    Rel(api_functions, api_client, "Usa interceptor HTTP")
    Rel(api_client, gateway, "HTTP REST con JWT", "HTTPS :8000")
    Rel(auth_provider, api_functions, "Login/Refresh calls")
    Rel(dashboard_page, api_functions, "Fetch data")
    Rel(dashboard_tecnico, api_functions, "Fetch incidencias + repuestos")
    Rel(equipo_detail, api_functions, "Fetch data")
    Rel(crud_pages, api_functions, "CRUD operations")
    Rel(reportes_page, api_functions, "Fetch preview + download CSV/PDF")
```

---

## Deployment Diagram (Docker Compose - Desarrollo)

```mermaid
graph TB
    subgraph "Docker Compose Network"
        subgraph "Frontend Container"
            FE["Next.js 16<br/>:3000<br/>Node 20 Alpine"]
        end

        subgraph "API Gateway Container"
            GW["FastAPI<br/>:8000<br/>Python 3.11<br/>JWT + RBAC + Proxy"]
        end

        subgraph "IoT Service Container"
            IOT["FastAPI<br/>:8001<br/>Python 3.11<br/>Ingesta + Equipos"]
        end

        subgraph "ML Service Container"
            ML["FastAPI<br/>:8002<br/>Python 3.11<br/>scikit-learn<br/>RF Models (~200MB)"]
        end

        subgraph "Ops Service Container"
            OPS["FastAPI<br/>:8003<br/>Python 3.11<br/>Gestion Operativa<br/>SMTP Client"]
        end

        subgraph "Database Container"
            DB[("PostgreSQL 15<br/>:5432<br/>airmonitoring DB<br/>pgdata volume")]
        end
    end

    subgraph "External"
        BROWSER["Browser<br/>localhost:3000"]
        CR310["Campbell CR310<br/>Datalogger IoT"]
        SMTP["Mailtrap SMTP<br/>sandbox.smtp.mailtrap.io:2525"]
    end

    BROWSER -->|"HTTPS"| FE
    FE -->|"HTTP REST"| GW
    CR310 -->|"POST /api/v1/iot/readings<br/>(ruta publica)"| GW

    GW -->|"/iot/*"| IOT
    GW -->|"/predictions/*, /alerts/*"| ML
    GW -->|"/incidencias/*, /calibraciones/*<br/>/usuarios/*, /reportes/*, /dashboard/*"| OPS

    IOT -->|"SQLAlchemy"| DB
    ML -->|"SQLAlchemy"| DB
    OPS -->|"SQLAlchemy"| DB
    OPS -->|"SMTP"| SMTP

    style FE fill:#3b82f6,color:#fff
    style GW fill:#f59e0b,color:#000
    style IOT fill:#10b981,color:#fff
    style ML fill:#8b5cf6,color:#fff
    style OPS fill:#ef4444,color:#fff
    style DB fill:#6b7280,color:#fff
```

---

## Data Flow Diagram - Flujo de Prediccion

```mermaid
sequenceDiagram
    participant CR310 as Campbell CR310
    participant GW as API Gateway :8000
    participant IOT as IoT Service :8001
    participant ML as ML Service :8002
    participant OPS as Ops Service :8003
    participant DB as PostgreSQL
    participant SMTP as SMTP Server

    Note over CR310,SMTP: Flujo de Ingesta + Prediccion + Alerta Automatica

    CR310->>GW: POST /api/v1/iot/readings<br/>{equipo: "T101", so2_ppb: 10.5, ...}
    Note over GW: Ruta publica (sin auth)
    GW->>IOT: Proxy POST /api/v1/iot/readings
    IOT->>DB: INSERT lecturas_iot
    IOT-->>GW: 201 Created
    GW-->>CR310: 201 Created

    Note over ML: Prediccion cada hora (o manual)
    ML->>DB: SELECT ultimas lecturas por device_id
    ML->>ML: Feature Engineering (122 features)<br/>Scale + RF Regressor (RUL)<br/>+ RF Classifier (failure_prob)
    ML->>DB: INSERT prediccion<br/>{failure_prob: 0.85, RUL: 25, risk: "alta"}
    ML->>DB: INSERT alerta<br/>{nivel_riesgo: "alta", estado: "activa"}

    Note over OPS: Evaluacion automatica de alertas
    OPS->>DB: SELECT alertas altas hoy para device_id
    alt >= 2 alertas altas mismo equipo en 1 dia
        OPS->>DB: INSERT incidencia tipo=correctiva, prioridad=alta
        OPS->>SMTP: Email notificacion nueva incidencia
    end

    Note over OPS: Al finalizar incidencia correctiva
    alt Incidencia correctiva -> estado: finalizado
        OPS->>DB: INSERT incidencia tipo=calibracion (auto-generada)
        OPS->>SMTP: Email notificacion calibracion pendiente
    end
```

---

## Entity Relationship Diagram

```mermaid
erDiagram
    EQUIPOS {
        int id PK
        string device_id UK
        string nombre
        string tipo
        string ubicacion
        string estado
        string serie
        string codigo_interno
        string modelo
        string marca
        date fecha_ingreso
        string rango_medicion
        string parametro_medicion
        string foto_equipo
        int datalogger_id
    }

    LECTURAS_IOT {
        int id PK
        int device_id FK
        datetime timestamp_lectura
        float so2_ppb
        float h2s_ppb
        float reaction_temp
        float izs_temp
        float pmt_temp
        float sample_flow
        float pressure
        float uv_lamp_intensity
        float box_temp
        float hvps_v
        float conv_temp
        float ozone_flow
        json raw_payload
        bool procesado
    }

    PREDICCIONES {
        int id PK
        string device_id
        string model_version
        float failure_probability
        int remaining_useful_life_days
        string risk_level
        json feature_snapshot
        datetime prediction_timestamp
    }

    ALERTAS {
        int id PK
        string device_id
        int prediccion_id FK
        string nivel_riesgo
        string descripcion
        string estado
    }

    USUARIOS {
        int id PK
        string email UK
        string nombre
        string apellido
        string rol
        string password_hash
        string estado
    }

    DATALOGGERS {
        int id PK
        string nombre
        string codigo_interno
        string numero_serie
        string ubicacion
        string estado
    }

    INCIDENCIAS {
        int id PK
        string device_id
        string tipo
        string descripcion
        string estado
        string prioridad
        int responsable_id FK
    }

    MANTENIMIENTOS_CORRECTIVOS {
        int id PK
        int incidencia_id FK
        string diagnostico
        string acciones_realizadas
        string conclusion
        datetime fecha_ejecucion
    }

    CALIBRACIONES {
        int id PK
        int incidencia_id FK
        string device_id
        datetime fecha_calibracion
        string nota
        string certificado_url
        int proveedor_id FK
    }

    REPUESTOS {
        int id PK
        string nombre
        string categoria
        string estado
    }

    MANTENIMIENTO_REPUESTOS {
        int mantenimiento_id FK
        int repuesto_id FK
    }

    PROVEEDORES_CALIBRACION {
        int id PK
        string nombre
        string estado
    }

    ARCHIVOS_ADJUNTOS {
        int id PK
        string entidad_tipo
        int entidad_id
        string filename
        string file_url
    }

    EQUIPOS ||--o{ LECTURAS_IOT : "tiene"
    PREDICCIONES ||--o{ ALERTAS : "genera"
    INCIDENCIAS ||--o| MANTENIMIENTOS_CORRECTIVOS : "tiene"
    INCIDENCIAS ||--o| CALIBRACIONES : "tiene"
    USUARIOS ||--o{ INCIDENCIAS : "responsable"
    MANTENIMIENTOS_CORRECTIVOS ||--o{ MANTENIMIENTO_REPUESTOS : "usa"
    REPUESTOS ||--o{ MANTENIMIENTO_REPUESTOS : "usado en"
    PROVEEDORES_CALIBRACION ||--o{ CALIBRACIONES : "realiza"
```

---

## CI/CD Pipeline

```mermaid
graph LR
    subgraph "Triggers"
        PUSH["Push to<br/>main / dev / qa"]
        PR["Pull Request"]
    end

    subgraph "Backend CI (backend-ci.yml)"
        MATRIX["Matrix Strategy<br/>4 services"]
        CHECKOUT_B["Checkout"]
        PYTHON["Setup Python 3.11"]
        DEPS["Install dependencies"]
        LINT["Flake8 Lint"]
        TEST["Pytest<br/>(with PostgreSQL service)"]
    end

    subgraph "Frontend CI (frontend-ci.yml)"
        CHECKOUT_F["Checkout"]
        NODE["Setup Node 20"]
        INSTALL["npm ci"]
        ESLINT["ESLint"]
        BUILD["Next.js Build"]
    end

    PUSH --> MATRIX
    PUSH --> CHECKOUT_F
    PR --> MATRIX
    PR --> CHECKOUT_F

    MATRIX --> CHECKOUT_B --> PYTHON --> DEPS --> LINT --> TEST
    CHECKOUT_F --> NODE --> INSTALL --> ESLINT --> BUILD

    style LINT fill:#f59e0b,color:#000
    style TEST fill:#10b981,color:#fff
    style ESLINT fill:#f59e0b,color:#000
    style BUILD fill:#3b82f6,color:#fff
```

---

## Resumen de Decisiones Arquitectonicas

| Decision | Eleccion | Justificacion |
|----------|----------|---------------|
| Patron de comunicacion | Proxy reverso centralizado (API Gateway) | Punto unico de auth, RBAC y entrada |
| Base de datos | PostgreSQL unico, esquemas separados por Alembic | Simplicidad MVP, migraciones independientes |
| FK entre servicios | Sin FK cross-service (device_id como string) | Desacoplamiento de microservicios |
| Autenticacion | JWT HS256 propio | Evitar dependencia AWS Cognito en MVP |
| ML Runtime | Modelos cargados en memoria al startup | Latencia minima en inferencia |
| Frontend SSR | Next.js con dynamic imports (Recharts) | Bundle optimizado, SSR-capable |
| RBAC Frontend | RouteGuard + rol-por-ruta en cliente | Tecnico ve solo /dashboard-tecnico; admin/coordinador acceden a /reportes |
| Email | SMTP directo (Mailtrap dev) | Simplicidad, sin dependencia SaaS |
| Almacenamiento archivos | URLs string (S3 futuro) | Defer infraestructura cloud post-MVP |
