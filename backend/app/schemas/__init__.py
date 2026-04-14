"""Pydantic schema package placeholder for request and response models."""

from app.schemas.agent_chat import (
    AgentChatMessageCreate,
    AgentChatMessageResponse,
    AgentChatThreadDetailResponse,
    AgentChatThreadResponse,
)
from app.schemas.auth import AuthMeResponse
from app.schemas.document import (
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadRequest,
    DocumentUploadResponse,
)
from app.schemas.knowledge import (
    KnowledgeReindexResponse,
    KnowledgeStatusSummary,
    ProjectKnowledgeQuery,
    ProjectKnowledgeQueryResponse,
)
from app.schemas.project import (
    MaterialTopic,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SdgSelection,
)
from app.schemas.reference_data import (
    CaptacaoRowResponse,
    GriStandardResponse,
    IndicatorTemplateResponse,
    OdsGoalResponse,
    OdsMetaResponse,
)
from app.schemas.report import (
    GriIndexEntry,
    ReportGapEntry,
    ReportListItem,
    ReportResponse,
    ReportSectionPayload,
    ReportSectionUpdateRequest,
)

__all__ = [
    "AuthMeResponse",
    "AgentChatMessageCreate",
    "AgentChatMessageResponse",
    "AgentChatThreadDetailResponse",
    "AgentChatThreadResponse",
    "CaptacaoRowResponse",
    "DocumentResponse",
    "DocumentUpdateRequest",
    "DocumentUploadRequest",
    "DocumentUploadResponse",
    "GriIndexEntry",
    "GriStandardResponse",
    "IndicatorTemplateResponse",
    "KnowledgeReindexResponse",
    "KnowledgeStatusSummary",
    "MaterialTopic",
    "OdsGoalResponse",
    "OdsMetaResponse",
    "ProjectCreate",
    "ProjectKnowledgeQuery",
    "ProjectKnowledgeQueryResponse",
    "ProjectResponse",
    "ProjectUpdate",
    "ReportGapEntry",
    "ReportListItem",
    "ReportResponse",
    "ReportSectionPayload",
    "ReportSectionUpdateRequest",
    "SdgSelection",
]
