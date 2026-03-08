from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "local"
    APP_NAME: str = "Brand Brain API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+psycopg://brandbrain:brandbrain@localhost:5432/brandbrain"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AI
    AI_DEFAULT_PROVIDER: str = "mock"
    AI_MODEL: str = ""  # empty = use provider default
    AI_CONFIDENTIAL_MODE: bool = False
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # SMTP (vazio = modo simulacao, sem envio real)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@brandbrain.dev"
    SMTP_FROM_NAME: str = "Brand Brain"

    # Storage
    STORAGE_BASE_PATH: str = "/data/storage"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
