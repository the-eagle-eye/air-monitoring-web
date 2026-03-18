from shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    SERVICE_NAME: str = "ops-service"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 2525
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@airmonitoring.oefa.gob.pe"
    FRONTEND_URL: str = "http://localhost:3000"


settings = Settings()
