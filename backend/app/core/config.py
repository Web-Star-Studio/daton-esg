from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    backend_port: int = 8000
    postgres_user: str = "worton"
    postgres_password: str = "worton"
    postgres_db: str = "worton_esg"
    database_url: str = (
        "postgresql+asyncpg://worton:worton@postgres:5432/worton_esg"
    )
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_endpoint_url: str = "http://localstack:4566"
    s3_bucket_name: str = "worton-esg-development"
    log_level: str = "INFO"
    log_json: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if Path("/.dockerenv").exists():
            return value

        parsed = urlsplit(value)
        if parsed.hostname != "postgres":
            return value

        port = parsed.port or 5432
        credentials = ""
        if parsed.username:
            credentials = parsed.username
            if parsed.password:
                credentials = f"{credentials}:{parsed.password}"
            credentials = f"{credentials}@"

        return urlunsplit(
            (
                parsed.scheme,
                f"{credentials}localhost:{port}",
                parsed.path,
                parsed.query,
                parsed.fragment,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
