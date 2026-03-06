import os


class WorkerSettings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://brandbrain:brandbrain@localhost:5432/brandbrain",
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Worker tuning
    POLL_INTERVAL_SECONDS: int = int(os.getenv("WORKER_POLL_INTERVAL", "30"))
    BATCH_SIZE: int = int(os.getenv("WORKER_BATCH_SIZE", "10"))
    MAX_RETRIES: int = int(os.getenv("WORKER_MAX_RETRIES", "3"))
    RETRY_BASE_DELAY_SECONDS: int = int(os.getenv("WORKER_RETRY_BASE_DELAY", "30"))
    RETRY_MULTIPLIER: int = int(os.getenv("WORKER_RETRY_MULTIPLIER", "4"))


settings = WorkerSettings()
