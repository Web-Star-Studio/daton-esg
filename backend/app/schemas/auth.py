from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class AuthMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cognito_sub: str | None
    email: str
    name: str | None
    role: UserRole
    created_at: datetime
