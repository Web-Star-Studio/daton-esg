"""add project agent chat thread and messages"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260413_0007"
down_revision = "20260413_0006"
branch_labels = None
depends_on = None


AGENT_CHAT_MESSAGE_ROLE = postgresql.ENUM(
    "user",
    "assistant",
    "system",
    name="agent_chat_message_role",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    AGENT_CHAT_MESSAGE_ROLE.create(bind, checkfirst=True)

    op.create_table(
        "agent_chat_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_agent_chat_threads_project_id"),
    )
    op.create_index(
        "ix_agent_chat_threads_project_id",
        "agent_chat_threads",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "agent_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", AGENT_CHAT_MESSAGE_ROLE, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("retrieval_query", sa.Text(), nullable=True),
        sa.Column(
            "retrieved_chunks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["agent_chat_threads.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_chat_messages_thread_id",
        "agent_chat_messages",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_chat_messages_project_id",
        "agent_chat_messages",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_chat_messages_project_id", table_name="agent_chat_messages")
    op.drop_index("ix_agent_chat_messages_thread_id", table_name="agent_chat_messages")
    op.drop_table("agent_chat_messages")
    op.drop_index("ix_agent_chat_threads_project_id", table_name="agent_chat_threads")
    op.drop_table("agent_chat_threads")

    bind = op.get_bind()
    AGENT_CHAT_MESSAGE_ROLE.drop(bind, checkfirst=True)
