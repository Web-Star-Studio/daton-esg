"""replace extraction pipeline with document drive directories"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260413_0005"
down_revision = "20260410_0004"
branch_labels = None
depends_on = None


DOCUMENT_PARSING_STATUS = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="document_parsing_status",
    create_type=False,
)
CLASSIFICATION_CONFIDENCE = postgresql.ENUM(
    "high",
    "medium",
    "low",
    name="classification_confidence",
    create_type=False,
)
EXTRACTION_REVIEW_STATUS = postgresql.ENUM(
    "pending",
    "approved",
    "corrected",
    "ignored",
    name="extraction_review_status",
    create_type=False,
)
EXTRACTION_SOURCE_KIND = postgresql.ENUM(
    "paragraph",
    "table_row",
    "table_cell",
    "sheet_row",
    name="extraction_source_kind",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("directory_key", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE documents
        SET directory_key = CASE esg_category
            WHEN 'Visão e Estratégia' THEN 'visao-estrategica-de-sustentabilidade'
            WHEN 'Governança' THEN 'governanca-corporativa'
            WHEN 'Ambiental' THEN 'gestao-ambiental'
            WHEN 'Social' THEN 'desempenho-social'
            WHEN 'Econômico' THEN 'gestao-de-desempenho-economico'
            WHEN 'Stakeholders' THEN 'relacionamento-com-stakeholders'
            WHEN 'Inovação' THEN 'inovacao-e-desenvolvimento-tecnologico'
            WHEN 'Normas' THEN 'relatorios-e-normas'
            WHEN 'Comunicação' THEN 'comunicacao-e-transparencia'
            WHEN 'Auditorias' THEN 'auditorias-e-avaliacoes'
            ELSE 'sem-categoria'
        END
        """
    )
    op.alter_column("documents", "directory_key", nullable=False)
    op.create_index(
        "ix_documents_directory_key",
        "documents",
        ["directory_key"],
        unique=False,
    )

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
    op.drop_column("documents", "parsing_error")
    op.drop_column("documents", "parsed_payload")
    op.drop_column("documents", "extracted_text")
    op.drop_column("documents", "parsing_status")
    op.drop_column("documents", "esg_category")

    bind = op.get_bind()
    EXTRACTION_SOURCE_KIND.drop(bind, checkfirst=True)
    EXTRACTION_REVIEW_STATUS.drop(bind, checkfirst=True)
    CLASSIFICATION_CONFIDENCE.drop(bind, checkfirst=True)
    DOCUMENT_PARSING_STATUS.drop(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    DOCUMENT_PARSING_STATUS.create(bind, checkfirst=True)
    CLASSIFICATION_CONFIDENCE.create(bind, checkfirst=True)
    EXTRACTION_REVIEW_STATUS.create(bind, checkfirst=True)
    EXTRACTION_SOURCE_KIND.create(bind, checkfirst=True)

    op.add_column(
        "documents",
        sa.Column("esg_category", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "parsing_status",
            DOCUMENT_PARSING_STATUS,
            nullable=False,
            server_default=sa.text("'pending'::document_parsing_status"),
        ),
    )
    op.add_column(
        "documents",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "parsed_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("parsing_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "classification_confidence",
            CLASSIFICATION_CONFIDENCE,
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE documents
        SET esg_category = CASE directory_key
            WHEN 'visao-estrategica-de-sustentabilidade' THEN 'Visão e Estratégia'
            WHEN 'governanca-corporativa' THEN 'Governança'
            WHEN 'gestao-ambiental' THEN 'Ambiental'
            WHEN 'desempenho-social' THEN 'Social'
            WHEN 'gestao-de-desempenho-economico' THEN 'Econômico'
            WHEN 'relacionamento-com-stakeholders' THEN 'Stakeholders'
            WHEN 'inovacao-e-desenvolvimento-tecnologico' THEN 'Inovação'
            WHEN 'relatorios-e-normas' THEN 'Normas'
            WHEN 'comunicacao-e-transparencia' THEN 'Comunicação'
            WHEN 'auditorias-e-avaliacoes' THEN 'Auditorias'
            ELSE NULL
        END
        """
    )

    op.create_table(
        "document_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_kind", EXTRACTION_SOURCE_KIND, nullable=False),
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
        sa.Column("confidence", CLASSIFICATION_CONFIDENCE, nullable=True),
        sa.Column(
            "review_status",
            EXTRACTION_REVIEW_STATUS,
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

    op.drop_index("ix_documents_directory_key", table_name="documents")
    op.drop_column("documents", "directory_key")
