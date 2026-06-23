from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "payments-service"
    api_key: str = Field(default="dev-api-key", min_length=1)

    database_url: str = (
        "postgresql+asyncpg://payments:payments@postgres:5432/payments"
    )
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    outbox_poll_interval_seconds: float = Field(default=1.0, gt=0)
    outbox_batch_size: int = Field(default=50, gt=0)
    outbox_max_attempts: int = Field(default=10, gt=0)
    outbox_base_delay_seconds: int = Field(default=2, gt=0)

    consumer_max_attempts: int = Field(default=3, gt=0)
    retry_base_delay_seconds: int = Field(default=2, gt=0)

    webhook_timeout_seconds: float = Field(default=5.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

