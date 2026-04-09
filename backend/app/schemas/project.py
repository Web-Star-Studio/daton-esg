from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import OrganizationSize, ProjectStatus


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
