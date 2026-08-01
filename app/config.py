from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://flowforge:flowforge@localhost:5432/flowforge"
    redis_url: str = "redis://localhost:6379/0"
    worker_recovery_idle_ms: int = 30000
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
