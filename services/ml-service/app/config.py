from shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    SERVICE_NAME: str = "ml-service"
    ML_ARTIFACTS_PATH: str = "/app/ml_artifacts"


settings = Settings()
