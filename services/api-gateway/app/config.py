from shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    SERVICE_NAME: str = "api-gateway"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Which ML backend to route /predictions/* and /alerts/* to.
    #   "legacy"    → ML_SERVICE_URL (v1 RUL, existing behavior)
    #   "isolation" → ML_ISOLATION_SERVICE_URL (v3 anomaly detection)
    ML_BACKEND: str = "legacy"
    ML_ISOLATION_SERVICE_URL: str = "http://ml-service-isolation:8004"


settings = Settings()
