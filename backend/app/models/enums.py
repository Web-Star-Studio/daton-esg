from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    CONSULTANT = "consultant"


class OrganizationSize(StrEnum):
    MICRO = "micro"
    SMALL = "pequena"
    MEDIUM = "média"
    LARGE = "grande"


class ProjectStatus(StrEnum):
    PLANNING = "planning"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    PRELIMINARY_REPORT = "preliminary_report"
    FINAL_REPORT = "final_report"
    ALIGNMENT = "alignment"
    LAYOUT = "layout"
    ARCHIVED = "archived"


class DocumentFileType(StrEnum):
    PDF = "pdf"
    XLSX = "xlsx"
    CSV = "csv"
    DOCX = "docx"


class DocumentIndexingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class AgentChatMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ReportStatus(StrEnum):
    GENERATING = "generating"
    FAILED = "failed"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    EXPORTED = "exported"
