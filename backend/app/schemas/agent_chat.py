from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentChatMessageRole


class AgentChatCitation(BaseModel):
    document_id: UUID | None
    filename: str
    directory_key: str | None
    chunk_index: int
    source_type: str
    score: float
    snippet: str


class AgentChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    thread_id: UUID
    project_id: UUID
    role: AgentChatMessageRole
    content: str
    citations: list[AgentChatCitation]
    created_at: datetime


class AgentChatThreadResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AgentChatThreadDetailResponse(BaseModel):
    thread: AgentChatThreadResponse
    messages: list[AgentChatMessageResponse]


class AgentChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
