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


class DocumentParsingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ClassificationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractionReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    CORRECTED = "corrected"
    IGNORED = "ignored"


class ExtractionSourceKind(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    SHEET_ROW = "sheet_row"


class ReportStatus(StrEnum):
    GENERATING = "generating"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    EXPORTED = "exported"
