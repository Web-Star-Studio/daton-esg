"""create reference data tables (gri, ods, captacao, indicator templates)"""

import sqlalchemy as sa

from alembic import op

revision = "20260413_0009"
down_revision = "20260413_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gri_standards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("family", sa.String(length=10), nullable=False),
        sa.Column("standard_text", sa.Text(), nullable=False),
        sa.UniqueConstraint("code", name="uq_gri_standards_code"),
    )
    op.create_index("ix_gri_standards_code", "gri_standards", ["code"], unique=False)
    op.create_index(
        "ix_gri_standards_family", "gri_standards", ["family"], unique=False
    )

    op.create_table(
        "ods_goals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ods_number", sa.Integer(), nullable=False),
        sa.Column("objetivo", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("ods_number", name="uq_ods_goals_ods_number"),
    )

    op.create_table(
        "ods_metas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ods_id", sa.Integer(), nullable=False),
        sa.Column("meta_code", sa.String(length=10), nullable=False),
        sa.Column("meta_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ods_id"],
            ["ods_goals.id"],
            ondelete="CASCADE",
            name="fk_ods_metas_ods_id",
        ),
    )
    op.create_index("ix_ods_metas_ods_id", "ods_metas", ["ods_id"])

    op.create_table(
        "captacao_matriz",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sessao", sa.String(length=64), nullable=False),
        sa.Column("tipo_dado", sa.String(length=255), nullable=False),
        sa.Column("gri_code", sa.String(length=20), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "fonte_documental",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "tipo_evidencia",
            sa.String(length=128),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.create_index("ix_captacao_matriz_sessao", "captacao_matriz", ["sessao"])
    op.create_index("ix_captacao_matriz_gri_code", "captacao_matriz", ["gri_code"])

    op.create_table(
        "indicator_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tema", sa.String(length=64), nullable=False),
        sa.Column("indicador", sa.String(length=255), nullable=False),
        sa.Column(
            "unidade",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.create_index("ix_indicator_templates_tema", "indicator_templates", ["tema"])


def downgrade() -> None:
    op.drop_index("ix_indicator_templates_tema", table_name="indicator_templates")
    op.drop_table("indicator_templates")
    op.drop_index("ix_captacao_matriz_gri_code", table_name="captacao_matriz")
    op.drop_index("ix_captacao_matriz_sessao", table_name="captacao_matriz")
    op.drop_table("captacao_matriz")
    op.drop_index("ix_ods_metas_ods_id", table_name="ods_metas")
    op.drop_table("ods_metas")
    op.drop_table("ods_goals")
    op.drop_index("ix_gri_standards_family", table_name="gri_standards")
    op.drop_index("ix_gri_standards_code", table_name="gri_standards")
    op.drop_table("gri_standards")
