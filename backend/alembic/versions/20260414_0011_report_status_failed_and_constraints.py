"""add FAILED report status, unique (project_id, version), partial unique index for at-most-one GENERATING per project, clean up stuck GENERATING reports"""

import sqlalchemy as sa

from alembic import op

revision = "20260414_0011"
down_revision = "20260414_0011a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Clean up any stuck GENERATING reports (older than 1 hour)
    # (FAILED enum value was added in 0011a)
    op.execute(
        "UPDATE reports SET status = 'failed' "
        "WHERE status = 'generating' "
        "AND updated_at < now() - interval '1 hour'"
    )

    # 3. Precheck: abort if duplicate (project_id, version) rows exist
    bind = op.get_bind()
    dupes = bind.execute(
        sa.text(
            "SELECT project_id, version, count(*) "
            "FROM reports "
            "GROUP BY project_id, version "
            "HAVING count(*) > 1"
        )
    ).fetchall()
    if dupes:
        raise RuntimeError(
            f"Cannot add unique constraint: {len(dupes)} duplicate "
            f"(project_id, version) rows found. Fix manually before "
            f"re-running migration."
        )

    # 4. Precheck: abort if multiple GENERATING reports per project
    multi_gen = bind.execute(
        sa.text(
            "SELECT project_id, count(*) "
            "FROM reports "
            "WHERE status = 'generating' "
            "GROUP BY project_id "
            "HAVING count(*) > 1"
        )
    ).fetchall()
    if multi_gen:
        raise RuntimeError(
            f"Cannot add partial unique index: {len(multi_gen)} projects "
            f"have multiple GENERATING reports. Fix manually before "
            f"re-running migration."
        )

    # 5. Add unique constraint on (project_id, version)
    op.create_unique_constraint(
        "uq_reports_project_version",
        "reports",
        ["project_id", "version"],
    )

    # 6. Add partial unique index: at most one GENERATING per project
    op.execute(
        "CREATE UNIQUE INDEX ix_reports_one_generating_per_project "
        "ON reports (project_id) "
        "WHERE status = 'generating'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_reports_one_generating_per_project")
    op.drop_constraint("uq_reports_project_version", "reports", type_="unique")
    # Note: cannot remove an enum value in PostgreSQL; FAILED remains
    # in the type but is functionally unused after downgrade.
