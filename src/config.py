import os
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):

    BREVO_API_KEY: str
    FRONTEND_URL: str
    BACKEND_URL: str
    EMAIL_FROM: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    CLIENT_ID: str
    CLIENT_SECRET: str


    # REDIS_URL: str = "redis://localhost:6379/0"
    # MAIL_USERNAME: str
    # MAIL_PASSWORD: str
    # MAIL_FROM: str
    # MAIL_PORT: int
    # MAIL_SERVER: str
    # MAIL_FROM_NAME: str
    # MAIL_STARTTLS: bool = True
    # MAIL_SSL_TLS: bool = False
    # USE_CREDENTIALS: bool = True
    # VALIDATE_CERTS: bool = True
    # DOMAIN: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


# broker_url = Config.REDIS_URL
# result_backend = Config.REDIS_URL
broker_connection_retry_on_startup = True
