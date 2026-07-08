# Air Monitoring - Sistema Predictivo de Mantenimiento

Sistema predictivo para reducir fallas de equipos de medicion directa de calidad de aire, basado en Machine Learning e IoT. Caso de estudio: laboratorio OEFA, Peru. Alineado con ISO/IEC 17025:2017.

## Arquitectura

Microservicios desacoplados con comunicacion HTTP REST:

```md
frontend (Next.js :3000)
    |
api-gateway (:8000)
    |
    +-- iot-service (:8001)    -> Ingesta y gestion de equipos/lecturas IoT
    +-- ml-service  (:8002)    -> Predicciones ML y alertas
    +-- ops-service (:8003)    -> Gestion operativa (incidencias, calibraciones, mantenimientos)
    |
PostgreSQL (:5432)
```

## Tech Stack

| Capa | Tecnologia |
|------|-----------|
| Frontend | React, Next.js, TypeScript, TailwindCSS, Recharts |
| Backend | Python 3.x, FastAPI |
| ML | scikit-learn (ensemble no supervisado: Autoencoder + Isolation Forest), pandas, numpy, joblib |
| Base de datos | PostgreSQL 15 |
| Contenedores | Docker, Docker Compose |
| CI/CD | GitHub Actions |

## Requisitos Previos

- Docker y Docker Compose
- Node.js 18+ (desarrollo frontend local)
- Python 3.11+ (desarrollo backend local)

## Inicio Rapido

### Con Docker Compose (recomendado)

```bash
# 1. Clonar el repositorio
git clone https://github.com/the-eagle-eye/air-monitoring-web.git
cd air-monitoring-web

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Levantar todos los servicios (migraciones + seed corren solas al arrancar)
docker compose up --build
#    Espera a que los 5 servicios esten "healthy".

# 4. Poblar el dashboard con actividad (lecturas -> ensemble -> salud/incidencias)
#    En otra terminal, con los contenedores arriba:
python scripts/simulate_multi_random.py --cycles 8 --interval 30
```

Servicios disponibles:

- Frontend: http://localhost:3000  (login: `admin@oefa.gob.pe` / `admin123`)
- API Gateway: http://localhost:8000
- IoT Service: http://localhost:8001
- ML Service: http://localhost:8002
- Ops Service: http://localhost:8003

> **Modelos del ensemble ya incluidos.** Los artefactos entrenados del monitor de
> salud (ensemble Autoencoder + Isolation Forest por estacion) estan versionados en
> `services/ml-service/ml_artifacts_ensemble_v1/` (5 estaciones: CA-CC-01, CA-CH-04,
> CA-CH-05, CA-ILO-01, CA-UCHU-01). No hay que entrenarlos ni pasar archivos por fuera:
> con `docker compose up` el ml-service los toma via bind-mount y el monitor funciona.
>
> **Orden importa:** los modelos deben estar presentes ANTES de levantar el ml-service
> (el registry cachea "sin modelo"). Si haces `git pull` con el servicio ya corriendo,
> reinicia el ml-service: `docker compose restart ml-service`.
>
> **Datos de demo:** la base arranca con el seed de migraciones (usuarios, repuestos,
> equipos). El paso 4 (`simulate_multi_random.py`) genera lecturas que pasan por el
> ensemble y pueblan salud/incidencias/tendencias — es lo que da vida al dashboard.
> Un equipo sin modelo entrenado se muestra como `SIN_DATOS` (comportamiento esperado).

### Desarrollo Local (sin Docker)

**Backend (cada servicio):**

```bash
cd services/iot-service  # o ml-service, ops-service, api-gateway
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Estructura del Proyecto

```ini
air_monitoring_project/
├── frontend/                  # Next.js + React + TypeScript
│   ├── src/
│   │   ├── app/               # Pages (dashboard, equipos, lecturas, etc.)
│   │   ├── components/        # Componentes React
│   │   ├── lib/api/           # Clientes API
│   │   └── types/             # Tipos TypeScript
│   └── ...
├── services/
│   ├── api-gateway/           # Proxy y autenticacion (Sprint 4)
│   ├── iot-service/           # Ingesta IoT, CRUD equipos, lecturas
│   ├── ml-service/            # Modelo ML, predicciones, alertas
│   │   ├── app/ml/            # Pipeline de entrenamiento y prediccion
│   │   └── ml_artifacts/      # Artefactos del modelo (generados)
│   └── ops-service/           # Incidencias, calibraciones, mantenimientos
├── shared/                    # Codigo compartido (database, config, models base)
├── docker-compose.yml
└── .github/workflows/         # CI/CD pipelines
```

## Modelo ML

Monitor de salud basado en un **ensemble no supervisado por estacion**: Autoencoder
(error de reconstruccion vs umbral θ) + Isolation Forest, unidos por una compuerta
**AND** (alerta solo si ambos detectores coinciden → evita falsos positivos).

- **Salida:** estado de salud `SANO / OBSERVADO / EN_RIESGO / CRITICO / SIN_DATOS`
  por equipo (endpoint `/api/v1/health-monitor`).
- **Por estacion:** cada equipo tiene su propio modelo y su θ (aprende su "normalidad").
  Un equipo sin modelo entrenado se reporta `SIN_DATOS` (fallback seguro, no alerta).
- **Artefactos versionados** en `services/ml-service/ml_artifacts_ensemble_v1/`
  (`scaler_<id>.pkl`, `autoencoder_<id>.pkl`, `iforest_<id>.pkl`, `theta_<id>.json`).

> El modelo Random Forest original (RUL / probabilidad de falla) fue retirado; ver
> `docs/spec-racionalizacion-dashboard-e-incidencias.md`.

### Entrenar / re-entrenar (offline, opcional)

Los modelos ya vienen versionados. Para re-entrenarlos se necesita el dataset historico
por estacion (no versionado) y el pipeline offline:

```bash
cd services/ml-service
python scripts/ensemble/01_build_dataset.py     # lee CSV historicos por estacion
python scripts/ensemble/02_train_autoencoder.py # -> autoencoder + theta
python scripts/ensemble/03_train_iforest.py     # -> iforest
# resultado: los .pkl/.json en ml_artifacts_ensemble_v1/
```

## Tests

```bash
# IoT Service
cd services/iot-service && PYTHONPATH=../.. python -m pytest tests/ -v

# ML Service
cd services/ml-service && PYTHONPATH=../.. python -m pytest tests/ -v

# Ops Service
cd services/ops-service && PYTHONPATH=../.. python -m pytest tests/ -v
```

## Reglas de Negocio

- **Anomalia confirmada por el ensemble** (AE supera θ **y** Isolation Forest coincide)
  -> se grada la severidad `OBSERVADO / EN_RIESGO / CRITICO`.
- **Regla de consolidacion** (ventana 24h): `OBSERVADO >= 5`, `EN_RIESGO >= 3`,
  `CRITICO >= 1` -> crea/escala una **incidencia correctiva** (un incidente abierto por
  equipo; escala prioridad, no duplica).
- **Prioridad** = matriz **impacto** (criticidad del equipo) x **urgencia** (severidad).
- **Incidencia correctiva finalizada** -> auto-crea incidencia de calibracion.
- **Ventana de mantenimiento (C9):** equipo con correctiva `en_ejecucion` -> el monitor
  silencia (no crea ni escala) hasta el cierre.
- **Gestion ITIL v4:** ciclo de vida de incidentes + Problemas (causa raiz). Ver
  `docs/flujo-itil-v4.md`.

## API

Base path: `/api/v1/`

| Servicio | Endpoints principales |
|----------|----------------------|
| iot-service | `GET/POST /iot/equipos`, `POST /iot/readings`, `GET /iot/readings/{deviceId}` |
| ml-service | `POST /predictions/run`, `GET /predictions/{deviceId}`, `GET /alerts` |
| ops-service | `GET/POST /incidencias`, `GET/POST /calibraciones`, `GET /repuestos`, `GET /dataloggers` |

Cada servicio expone `GET /health` para health checks.

## Licencia

Proyecto academico - Universidad Peruana de Ciencias (UPC) - PI2
