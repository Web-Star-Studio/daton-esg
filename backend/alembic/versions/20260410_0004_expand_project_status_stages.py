"""expand project_status enum to 7 report stages"""

from alembic import op

revision = "20260410_0004"
down_revision = "20260410_0003"
branch_labels = None
depends_on = None

NEW_VALUES = (
    "planning",
    "collecting",
    "analyzing",
    "preliminary_report",
    "final_report",
    "alignment",
    "layout",
    "archived",
)

OLD_VALUES = ("collecting", "generating", "reviewing", "finalized", "archived")


def upgrade() -> None:
    # 1. Convert column to text so we can remap values freely.
    op.execute("ALTER TABLE projects ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE text USING status::text")
    op.execute("DROP TYPE project_status")

    # 2. Remap old values to new ones.
    op.execute(
        "UPDATE projects SET status = 'preliminary_report' WHERE status = 'generating'"
    )
    op.execute("UPDATE projects SET status = 'alignment' WHERE status = 'reviewing'")
    op.execute("UPDATE projects SET status = 'layout' WHERE status = 'finalized'")

    # 3. Create new enum and cast column back.
    op.execute(
        "CREATE TYPE project_status AS ENUM ("
        + ", ".join(f"'{v}'" for v in NEW_VALUES)
        + ")"
    )
    op.execute(
        "ALTER TABLE projects "
        "ALTER COLUMN status TYPE project_status USING status::project_status"
    )
    op.execute(
        "ALTER TABLE projects "
        "ALTER COLUMN status SET DEFAULT 'planning'::project_status"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE projects ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE text USING status::text")
    op.execute("DROP TYPE project_status")

    # Remap back.
    op.execute(
        "UPDATE projects SET status = 'collecting'"
        " WHERE status IN ('planning', 'analyzing')"
    )
    op.execute(
        "UPDATE projects SET status = 'generating'"
        " WHERE status IN ('preliminary_report', 'final_report')"
    )
    op.execute("UPDATE projects SET status = 'reviewing' WHERE status = 'alignment'")
    op.execute("UPDATE projects SET status = 'finalized' WHERE status = 'layout'")

    op.execute(
        "CREATE TYPE project_status AS ENUM ("
        + ", ".join(f"'{v}'" for v in OLD_VALUES)
        + ")"
    )
    op.execute(
        "ALTER TABLE projects "
        "ALTER COLUMN status TYPE project_status USING status::project_status"
    )
    op.execute(
        "ALTER TABLE projects "
        "ALTER COLUMN status SET DEFAULT 'collecting'::project_status"
    )
