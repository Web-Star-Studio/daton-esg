import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import SecretStr, field_validator, model_validator
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
    openai_api_key: SecretStr | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    pinecone_api_key: SecretStr | None = None
    pinecone_index_name: str | None = None
    pinecone_index_host: str | None = None
    rag_chunk_size_chars: int = 2000
    rag_chunk_overlap_chars: int = 300
    rag_tabular_rows_per_chunk: int = 25
    openai_chat_model: str = "gpt-4.1-mini"
    openai_chat_temperature: float = 0.0
    openai_chat_max_output_tokens: int = 1200
    agent_chat_retrieval_top_k: int = 8
    agent_chat_min_score: float = 0.35
    agent_chat_history_limit: int = 12
    agent_chat_system_prompt_version: str = "v1"
    gri_reference_namespace: str = "__reference__gri-2021-pt"
    gri_reference_top_k: int = 3
    report_generation_model: str = "gpt-4.1-mini"
    report_generation_temperature: float = 0.0
    report_generation_max_output_tokens: int = 6000
    report_rag_top_k: int = 10
    report_min_section_ratio: float = 0.6
    report_max_section_ratio: float = 1.4
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
        issuer = (
            self.aws_cognito_issuer
            or f"https://cognito-idp.{self.aws_cognito_region}.amazonaws.com/"
            f"{self.aws_cognito_user_pool_id}"
        )
        self.aws_cognito_issuer = issuer
        self.aws_cognito_jwks_url = (
            self.aws_cognito_jwks_url or f"{issuer}/.well-known/jwks.json"
        )
        if self.rag_chunk_overlap_chars >= self.rag_chunk_size_chars:
            raise ValueError("rag_chunk_overlap_chars must be smaller than chunk size")
        return self

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        scheme = parsed.scheme
        if scheme in {"postgres", "postgresql", "postgresql+psycopg2"}:
            scheme = "postgresql+asyncpg"
        elif "+asyncpg" not in scheme:
            scheme = "postgresql+asyncpg"

        if cls.is_container_environment() or parsed.hostname != "postgres":
            return urlunsplit(
                (
                    scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.query,
                    parsed.fragment,
                )
            )

        port = parsed.port or 5432
        credentials = ""
        if parsed.username:
            credentials = parsed.username
            if parsed.password:
                credentials = f"{credentials}:{parsed.password}"
            credentials = f"{credentials}@"

        return urlunsplit(
            (
                scheme,
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

    @field_validator(
        "pinecone_index_name",
        "pinecone_index_host",
        "openai_chat_model",
        "agent_chat_system_prompt_version",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("rag_chunk_size_chars", "rag_chunk_overlap_chars")
    @classmethod
    def validate_chunk_sizes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Chunk sizes must be greater than zero")
        return value

    @field_validator("rag_tabular_rows_per_chunk")
    @classmethod
    def validate_tabular_rows_per_chunk(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Tabular rows per chunk must be greater than zero")
        return value

    @field_validator("openai_chat_temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("openai_chat_temperature must be between 0 and 1")
        return value

    @field_validator(
        "openai_chat_max_output_tokens",
        "agent_chat_retrieval_top_k",
        "agent_chat_history_limit",
    )
    @classmethod
    def validate_positive_chat_settings(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Chat settings must be greater than zero")
        return value

    @field_validator("agent_chat_min_score")
    @classmethod
    def validate_agent_chat_min_score(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("agent_chat_min_score must be between 0 and 1")
        return value

    @staticmethod
    def is_container_environment() -> bool:
        return (
            Path("/.dockerenv").exists()
            or Path("/run/.containerenv").exists()
            or os.getenv("DOCKER_CONTAINER") is not None
            or os.getenv("PODMAN_CONTAINER") is not None
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
