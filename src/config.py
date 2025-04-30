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
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    SESSION_SECRET_KEY: str
    RESEND_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


# broker_url = Config.REDIS_URL
# result_backend = Config.REDIS_URL
broker_connection_retry_on_startup = True
