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
| ML | scikit-learn (Random Forest), pandas, numpy, joblib |
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
# Clonar el repositorio
git clone https://github.com/the-eagle-eye/air-monitoring-web.git
cd air-monitoring-web

# Copiar variables de entorno
cp .env.example .env

# Levantar todos los servicios
docker compose up --build
```

Servicios disponibles:

- Frontend: http://localhost:3000
- API Gateway: http://localhost:8000
- IoT Service: http://localhost:8001
- ML Service: http://localhost:8002
- Ops Service: http://localhost:8003

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

- **Algoritmo:** Random Forest (Regresor para RUL + Clasificador para probabilidad de falla)
- **Features:** 122 features derivadas de 12 sensores con ventanas temporales (1h, 6h, 24h)
- __Output:__ `failure_probability` (0-1), `remaining_useful_life_days` (int), `risk_level` (low/medium/high)

### Entrenar el modelo

```bash
cd services/ml-service
PYTHONPATH=../.. python -m app.ml.train_model --output-dir ml_artifacts
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

- **RUL <= 30 dias** -> Alerta alta
- **RUL 31-60 dias** -> Alerta media
- **RUL > 60 dias** -> Monitoreo normal
- **>= 2 alertas altas/dia mismo equipo** -> Incidencia correctiva automatica
- **Incidencia correctiva finalizada** -> Auto-crea incidencia de calibracion

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
