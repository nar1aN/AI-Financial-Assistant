from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ML-сервис
    ML_SERVICE_URL: str = "http://localhost:5001"

    # PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ai_financial"

    # FastAPI
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Ollama
    OLLAMA_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # TODO: добавить настройки Redis когда будем кэшировать прогнозы
    # REDIS_URL: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()