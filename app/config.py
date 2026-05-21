from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres
    postgres_user: str = Field(default="habit")
    postgres_password: str = Field(default="habit")
    postgres_db: str = Field(default="habit_tracker")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)

    # Mongo
    mongo_user: str = Field(default="habit")
    mongo_password: str = Field(default="habit")
    mongo_host: str = Field(default="localhost")
    mongo_port: int = Field(default=27017)
    mongo_db: str = Field(default="habit_tracker")

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)

    # App
    app_env: str = Field(default="development")

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mongo_uri(self) -> str:
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/?authSource=admin"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
