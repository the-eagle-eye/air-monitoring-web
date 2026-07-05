from shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    SERVICE_NAME: str = "ml-service"


settings = Settings()
