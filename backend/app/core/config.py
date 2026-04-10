import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    backend_port: int = 8000
    postgres_user: str = "worton"
    postgres_password: str = "worton"
    postgres_db: str = "worton_esg"
    database_url: str = "postgresql+asyncpg://worton:worton@postgres:5432/worton_esg"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_endpoint_url: str = "http://localstack:4566"
    s3_bucket_name: str = "worton-esg-development"
    aws_textract_region: str | None = None
    document_parsing_pdf_provider: str = "auto"
    anthropic_api_key: str | None = None
    classification_model: str = "claude-sonnet-4-6-20250514"
    classification_temperature: float = 0.0
    aws_cognito_region: str = "us-east-1"
    aws_cognito_user_pool_id: str = "us-east-1_example123"
    aws_cognito_app_client_id: str = "exampleclientid1234567890"
    aws_cognito_issuer: str | None = None
    aws_cognito_jwks_url: str | None = None
    log_level: str = "INFO"
    log_json: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def derive_cognito_urls(self) -> "Settings":
        self.aws_textract_region = (
            self.aws_textract_region.strip()
            if self.aws_textract_region and self.aws_textract_region.strip()
            else self.aws_region
        )
        issuer = (
            self.aws_cognito_issuer
            or f"https://cognito-idp.{self.aws_cognito_region}.amazonaws.com/"
            f"{self.aws_cognito_user_pool_id}"
        )
        self.aws_cognito_issuer = issuer
        self.aws_cognito_jwks_url = (
            self.aws_cognito_jwks_url or f"{issuer}/.well-known/jwks.json"
        )
        return self

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if cls.is_container_environment():
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

    @field_validator("aws_endpoint_url", mode="after")
    @classmethod
    def normalize_aws_endpoint_url(cls, value: str) -> str:
        if not value:
            return value

        if cls.is_container_environment():
            return value

        parsed = urlsplit(value)
        if parsed.hostname != "localstack":
            return value

        port = parsed.port or 4566
        return urlunsplit(
            (
                parsed.scheme,
                f"localhost:{port}",
                parsed.path,
                parsed.query,
                parsed.fragment,
            )
        )

    @staticmethod
    def is_container_environment() -> bool:
        return (
            Path("/.dockerenv").exists()
            or Path("/run/.containerenv").exists()
            or os.getenv("DOCKER_CONTAINER") is not None
            or os.getenv("PODMAN_CONTAINER") is not None
        )

    @field_validator("classification_temperature", mode="after")
    @classmethod
    def validate_classification_temperature(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                "classification_temperature must be between 0.0 and 1.0"
            )
        return value

    @field_validator("document_parsing_pdf_provider", mode="after")
    @classmethod
    def validate_document_parsing_pdf_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed_values = {"auto", "textract", "local"}
        if normalized not in allowed_values:
            allowed = ", ".join(sorted(allowed_values))
            raise ValueError(f"document_parsing_pdf_provider must be one of: {allowed}")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
