"""extraction runs and suggestions for materiality and indicators auto-fill"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260417_0016"
down_revision = "20260416_0015"
branch_labels = None
depends_on = None


EXTRACTION_RUN_KIND = postgresql.ENUM(
    "materiality",
    "indicators",
    "both",
    name="extraction_run_kind",
    create_type=False,
)
EXTRACTION_RUN_STATUS = postgresql.ENUM(
    "running",
    "completed",
    "failed",
    "partial",
    name="extraction_run_status",
    create_type=False,
)
EXTRACTION_TARGET_KIND = postgresql.ENUM(
    "material_topic",
    "sdg_goal",
    "indicator_value",
    name="extraction_target_kind",
    create_type=False,
)
EXTRACTION_CONFIDENCE = postgresql.ENUM(
    "high",
    "medium",
    "low",
    name="extraction_confidence",
    create_type=False,
)
EXTRACTION_SUGGESTION_STATUS = postgresql.ENUM(
    "pending",
    "accepted",
    "rejected",
    "edited",
    name="extraction_suggestion_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    EXTRACTION_RUN_KIND.create(bind, checkfirst=True)
    EXTRACTION_RUN_STATUS.create(bind, checkfirst=True)
    EXTRACTION_TARGET_KIND.create(bind, checkfirst=True)
    EXTRACTION_CONFIDENCE.create(bind, checkfirst=True)
    EXTRACTION_SUGGESTION_STATUS.create(bind, checkfirst=True)

    op.create_table(
        "extraction_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", EXTRACTION_RUN_KIND, nullable=False),
        sa.Column(
            "status",
            EXTRACTION_RUN_STATUS,
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_used", sa.String(length=128), nullable=True),
        sa.Column(
            "documents_considered",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "summary_stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extraction_runs_project_id",
        "extraction_runs",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "extraction_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_kind", EXTRACTION_TARGET_KIND, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("confidence", EXTRACTION_CONFIDENCE, nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "conflict_with_existing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "existing_value_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            EXTRACTION_SUGGESTION_STATUS,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["extraction_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extraction_suggestions_run_id",
        "extraction_suggestions",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_suggestions_project_status",
        "extraction_suggestions",
        ["project_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_extraction_suggestions_project_status",
        table_name="extraction_suggestions",
    )
    op.drop_index(
        "ix_extraction_suggestions_run_id", table_name="extraction_suggestions"
    )
    op.drop_table("extraction_suggestions")
    op.drop_index("ix_extraction_runs_project_id", table_name="extraction_runs")
    op.drop_table("extraction_runs")

    bind = op.get_bind()
    EXTRACTION_SUGGESTION_STATUS.drop(bind, checkfirst=True)
    EXTRACTION_CONFIDENCE.drop(bind, checkfirst=True)
    EXTRACTION_TARGET_KIND.drop(bind, checkfirst=True)
    EXTRACTION_RUN_STATUS.drop(bind, checkfirst=True)
    EXTRACTION_RUN_KIND.drop(bind, checkfirst=True)
