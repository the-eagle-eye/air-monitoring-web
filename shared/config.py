from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql://airmon:airmon123@db:5432/airmonitoring"
    )
    IOT_SERVICE_URL: str = "http://iot-service:8001"
    ML_SERVICE_URL: str = "http://ml-service:8002"
    OPS_SERVICE_URL: str = "http://ops-service:8003"
    API_GATEWAY_URL: str = "http://api-gateway:8000"

    class Config:
        env_file = ".env"
