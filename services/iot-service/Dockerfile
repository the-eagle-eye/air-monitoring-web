FROM python:3.11-slim

WORKDIR /app

COPY services/iot-service/requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=3 -r requirements.txt

COPY shared/ /app/shared/
COPY services/iot-service/app/ /app/app/
COPY services/iot-service/migrations/ /app/migrations/
COPY services/iot-service/alembic.ini /app/alembic.ini
COPY services/iot-service/tests/ /app/tests/

ENV PYTHONPATH="/app"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"]
