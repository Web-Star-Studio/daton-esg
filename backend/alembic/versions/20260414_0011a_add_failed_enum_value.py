"""add FAILED to report_status enum (must run outside transaction)"""

from alembic import op

revision = "20260414_0011a"
down_revision = "20260413_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in PostgreSQL.
    # Commit the current transaction first, then add the value.
    op.execute("COMMIT")
    op.execute("ALTER TYPE report_status ADD VALUE IF NOT EXISTS 'failed'")


def downgrade() -> None:
    # Cannot remove an enum value in PostgreSQL; leave it in place.
    pass
