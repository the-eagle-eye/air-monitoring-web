FROM python:3.11-slim

WORKDIR /app

COPY services/ml-service/requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=3 -r requirements.txt

COPY shared/ /app/shared/
COPY services/ml-service/app/ /app/app/
COPY services/ml-service/ml_artifacts/ /app/ml_artifacts/
COPY services/ml-service/migrations/ /app/migrations/
COPY services/ml-service/alembic.ini /app/alembic.ini
COPY services/ml-service/tests/ /app/tests/

ENV PYTHONPATH="/app"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"]
