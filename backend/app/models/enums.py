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
    COLLECTING = "collecting"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    FINALIZED = "finalized"
    ARCHIVED = "archived"


class DocumentFileType(StrEnum):
    PDF = "pdf"
    XLSX = "xlsx"
    CSV = "csv"
    DOCX = "docx"


class DocumentParsingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportStatus(StrEnum):
    GENERATING = "generating"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    EXPORTED = "exported"
