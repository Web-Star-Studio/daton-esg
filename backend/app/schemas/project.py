from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import OrganizationSize, ProjectStatus


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
    base_year: int
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


class ProjectUpdate(BaseModel):
    org_name: str | None = None
    org_sector: str | None = None
    org_size: OrganizationSize | None = None
    org_location: str | None = None
    base_year: int | None = None
    scope: str | None = None
    status: ProjectStatus | None = None
    material_topics: dict[str, Any] | list[Any] | None = None
    sdg_goals: dict[str, Any] | list[Any] | None = None

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
    created_at: datetime
    updated_at: datetime
