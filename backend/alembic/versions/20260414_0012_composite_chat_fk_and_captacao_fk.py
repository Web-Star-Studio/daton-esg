"""add composite FK on chat messages + FK on captacao_matriz.gri_code

Forward-only migration (does not edit 0007/0008 in place).

1. agent_chat_threads: add unique constraint on (id, project_id) to support
   the composite child FK.
2. agent_chat_messages: drop the standalone project_id FK to projects.id,
   add a composite FK (thread_id, project_id) -> (id, project_id) on
   agent_chat_threads.
3. captacao_matriz: add FK gri_code -> gri_standards.code.
"""

from alembic import op

revision = "20260414_0012"
down_revision = "20260414_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Supporting unique constraint on threads for the composite FK
    op.create_unique_constraint(
        "uq_agent_chat_threads_id_project_id",
        "agent_chat_threads",
        ["id", "project_id"],
    )

    # 2. Drop standalone project_id FK on messages, add composite FK
    # First find and drop the existing FK constraint on project_id
    op.drop_constraint(
        "agent_chat_messages_project_id_fkey",
        "agent_chat_messages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_agent_chat_messages_thread_project",
        "agent_chat_messages",
        "agent_chat_threads",
        ["thread_id", "project_id"],
        ["id", "project_id"],
        ondelete="CASCADE",
    )

    # 3. Add FK on captacao_matriz.gri_code -> gri_standards.code
    op.create_foreign_key(
        "fk_captacao_matriz_gri_code",
        "captacao_matriz",
        "gri_standards",
        ["gri_code"],
        ["code"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Remove captacao FK
    op.drop_constraint(
        "fk_captacao_matriz_gri_code",
        "captacao_matriz",
        type_="foreignkey",
    )

    # Remove composite FK, restore standalone project_id FK
    op.drop_constraint(
        "fk_agent_chat_messages_thread_project",
        "agent_chat_messages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "agent_chat_messages_project_id_fkey",
        "agent_chat_messages",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Remove supporting unique constraint
    op.drop_constraint(
        "uq_agent_chat_threads_id_project_id",
        "agent_chat_threads",
        type_="unique",
    )
