from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # Postgres — either provide a full DATABASE_URL, or individual fields
    database_url: str | None = Field(default=None)
    postgres_user: str = Field(default="habit")
    postgres_password: str = Field(default="habit")
    postgres_db: str = Field(default="habit_tracker")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)

    # Mongo — either provide a full MONGO_URI (Atlas, etc.) or individual fields
    mongo_uri_override: str | None = Field(default=None, alias="MONGO_URI")
    mongo_user: str = Field(default="habit")
    mongo_password: str = Field(default="habit")
    mongo_host: str = Field(default="localhost")
    mongo_port: int = Field(default=27017)
    mongo_db: str = Field(default="habit_tracker")

    # Redis — either provide a full REDIS_URL or individual fields
    redis_url_override: str | None = Field(default=None, alias="REDIS_URL")
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)

    # App
    app_env: str = Field(default="development")

    # Auth (Phase 3 will harden — proper secret rotation, refresh tokens, rate limit)
    jwt_secret: str = Field(default="dev-secret-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expires_minutes: int = Field(default=60 * 24 * 7)  # 7 days

    @property
    def postgres_dsn(self) -> str:
        # Render-style DATABASE_URL takes precedence; convert to asyncpg dialect.
        if self.database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                url = "postgresql+asyncpg://" + url[len("postgres://") :]
            elif url.startswith("postgresql://"):
                url = "postgresql+asyncpg://" + url[len("postgresql://") :]
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mongo_uri(self) -> str:
        # Full URI (e.g. MongoDB Atlas SRV string) takes precedence.
        if self.mongo_uri_override:
            return self.mongo_uri_override
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/?authSource=admin"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_url_override:
            return self.redis_url_override
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
