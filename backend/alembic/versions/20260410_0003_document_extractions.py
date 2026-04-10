"""add document extractions and classification summary"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260410_0003"
down_revision = "20260409_0002"
branch_labels = None
depends_on = None


classification_confidence = postgresql.ENUM(
    "high",
    "medium",
    "low",
    name="classification_confidence",
    create_type=False,
)
extraction_review_status = postgresql.ENUM(
    "pending",
    "approved",
    "corrected",
    "ignored",
    name="extraction_review_status",
    create_type=False,
)
extraction_source_kind = postgresql.ENUM(
    "paragraph",
    "table_row",
    "table_cell",
    "sheet_row",
    name="extraction_source_kind",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    classification_confidence.create(bind, checkfirst=True)
    extraction_review_status.create(bind, checkfirst=True)
    extraction_source_kind.create(bind, checkfirst=True)

    op.add_column(
        "documents",
        sa.Column(
            "classification_confidence",
            classification_confidence,
            nullable=True,
        ),
    )

    op.create_table(
        "document_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_kind", extraction_source_kind, nullable=False),
        sa.Column(
            "source_locator",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("source_snippet", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("original_unit", sa.String(length=64), nullable=True),
        sa.Column("original_period", sa.String(length=64), nullable=True),
        sa.Column("original_esg_category", sa.String(length=255), nullable=True),
        sa.Column("corrected_value", sa.Text(), nullable=True),
        sa.Column("corrected_unit", sa.String(length=64), nullable=True),
        sa.Column("corrected_period", sa.String(length=64), nullable=True),
        sa.Column("corrected_esg_category", sa.String(length=255), nullable=True),
        sa.Column("confidence", classification_confidence, nullable=True),
        sa.Column(
            "review_status",
            extraction_review_status,
            nullable=False,
            server_default=sa.text("'pending'::extraction_review_status"),
        ),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_extractions_project_id",
        "document_extractions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_extractions_document_id",
        "document_extractions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_extractions_review_status",
        "document_extractions",
        ["review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_extractions_review_status",
        table_name="document_extractions",
    )
    op.drop_index(
        "ix_document_extractions_document_id",
        table_name="document_extractions",
    )
    op.drop_index(
        "ix_document_extractions_project_id",
        table_name="document_extractions",
    )
    op.drop_table("document_extractions")
    op.drop_column("documents", "classification_confidence")

    bind = op.get_bind()
    extraction_source_kind.drop(bind, checkfirst=True)
    extraction_review_status.drop(bind, checkfirst=True)
    classification_confidence.drop(bind, checkfirst=True)
