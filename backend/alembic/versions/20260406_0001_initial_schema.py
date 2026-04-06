"""initial schema"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260406_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role = postgresql.ENUM("admin", "consultant", name="user_role", create_type=False)
organization_size = postgresql.ENUM(
    "micro",
    "pequena",
    "média",
    "grande",
    name="organization_size",
    create_type=False,
)
project_status = postgresql.ENUM(
    "collecting",
    "generating",
    "reviewing",
    "finalized",
    "archived",
    name="project_status",
    create_type=False,
)
document_file_type = postgresql.ENUM(
    "pdf",
    "xlsx",
    "csv",
    "docx",
    name="document_file_type",
    create_type=False,
)
document_parsing_status = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="document_parsing_status",
    create_type=False,
)
report_status = postgresql.ENUM(
    "generating",
    "draft",
    "reviewed",
    "exported",
    name="report_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    user_role.create(bind, checkfirst=True)
    organization_size.create(bind, checkfirst=True)
    project_status.create(bind, checkfirst=True)
    document_file_type.create(bind, checkfirst=True)
    document_parsing_status.create(bind, checkfirst=True)
    report_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cognito_sub", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cognito_sub"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_name", sa.String(length=255), nullable=False),
        sa.Column("org_sector", sa.String(length=255), nullable=True),
        sa.Column("org_size", organization_size, nullable=True),
        sa.Column("org_location", sa.String(length=255), nullable=True),
        sa.Column("base_year", sa.Integer(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column(
            "status",
            project_status,
            server_default=sa.text("'collecting'::project_status"),
            nullable=False,
        ),
        sa.Column(
            "material_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("sdg_goals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", document_file_type, nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "parsing_status",
            document_parsing_status,
            server_default=sa.text("'pending'::document_parsing_status"),
            nullable=False,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("esg_category", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            report_status,
            server_default=sa.text("'generating'::report_status"),
            nullable=False,
        ),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("indicators", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("charts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("gri_index", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("gaps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exported_docx_s3", sa.String(length=512), nullable=True),
        sa.Column("exported_pdf_s3", sa.String(length=512), nullable=True),
        sa.Column("llm_tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_table("reports")
    op.drop_table("documents")
    op.drop_table("projects")
    op.drop_table("users")

    report_status.drop(bind, checkfirst=True)
    document_parsing_status.drop(bind, checkfirst=True)
    document_file_type.drop(bind, checkfirst=True)
    project_status.drop(bind, checkfirst=True)
    organization_size.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
