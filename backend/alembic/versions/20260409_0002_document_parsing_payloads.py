"""add document parsing payload fields"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260409_0002"
down_revision = "20260406_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "parsed_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "documents",
        sa.Column("parsing_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "parsing_error")
    op.drop_column("documents", "parsed_payload")
