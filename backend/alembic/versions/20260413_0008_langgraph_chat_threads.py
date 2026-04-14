"""allow multiple project chat threads and reset legacy history"""

import sqlalchemy as sa

from alembic import op

revision = "20260413_0008"
down_revision = "20260413_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM agent_chat_messages")
    op.execute("DELETE FROM agent_chat_threads")
    op.drop_constraint(
        "uq_agent_chat_threads_project_id",
        "agent_chat_threads",
        type_="unique",
    )
    op.add_column(
        "agent_chat_threads",
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text("'Nova conversa'"),
        ),
    )


def downgrade() -> None:
    op.execute("DELETE FROM agent_chat_messages")
    op.execute("DELETE FROM agent_chat_threads")
    op.drop_column("agent_chat_threads", "title")
    op.create_unique_constraint(
        "uq_agent_chat_threads_project_id",
        "agent_chat_threads",
        ["project_id"],
    )
