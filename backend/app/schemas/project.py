from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import OrganizationSize, ProjectStatus


class MaterialTopic(BaseModel):
    """Material topic with ESG pillar and priority."""

    pillar: Literal["E", "S", "G"]
    topic: str = Field(min_length=1, max_length=255)
    priority: int = Field(ge=1, le=5)

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("topic cannot be blank")
        return normalized


class IndicatorValue(BaseModel):
    """A single indicator value entered by the consultant."""

    tema: str = Field(min_length=1, max_length=64)
    indicador: str = Field(min_length=1, max_length=255)
    unidade: str = Field(max_length=64, default="")
    value: str = Field(max_length=255)


class SdgSelection(BaseModel):
    """One selected SDG with optional consultant narrative about the org's alignment."""

    ods_number: int = Field(ge=1, le=17)
    objetivo: str
    acao: str = ""
    indicador: str = ""
    resultado: str = ""


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


class ProjectCreate(BaseModel):
    org_name: str
    org_sector: str | None = None
    org_size: OrganizationSize | None = None
    org_location: str | None = None
    base_year: int = Field(ge=1900)
    scope: str | None = None

    @field_validator("org_name")
    @classmethod
    def validate_org_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Organization name is required")
        return normalized

    @field_validator("org_sector", "org_location", "scope", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("base_year")
    @classmethod
    def validate_base_year(cls, value: int) -> int:
        current_year = date.today().year
        if value > current_year:
            raise ValueError(f"Base year must be less than or equal to {current_year}")
        return value


class ProjectUpdate(BaseModel):
    org_name: str | None = None
    org_sector: str | None = None
    org_size: OrganizationSize | None = None
    org_location: str | None = None
    base_year: int | None = Field(default=None, ge=1900)
    scope: str | None = None
    status: ProjectStatus | None = None
    material_topics: list[MaterialTopic] | None = None
    sdg_goals: list[SdgSelection] | None = None
    indicator_values: list[IndicatorValue] | None = None

    @field_validator("org_name")
    @classmethod
    def validate_org_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("Organization name is required")
        return normalized

    @field_validator("org_sector", "org_location", "scope", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("base_year")
    @classmethod
    def validate_base_year(cls, value: int | None) -> int | None:
        if value is None:
            return None

        current_year = date.today().year
        if value > current_year:
            raise ValueError(f"Base year must be less than or equal to {current_year}")
        return value


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_name: str
    org_sector: str | None
    org_size: OrganizationSize | None
    org_location: str | None
    base_year: int
    scope: str | None
    status: ProjectStatus
    material_topics: dict[str, Any] | list[Any] | None
    sdg_goals: dict[str, Any] | list[Any] | None
    indicator_values: list[Any] | None
    created_at: datetime
    updated_at: datetime
