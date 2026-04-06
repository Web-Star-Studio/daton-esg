from functools import lru_cache

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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
