"""indicator catalog v2: GRI codes, groupings, computed fields, reseed"""

import sqlalchemy as sa

from alembic import op

revision = "20260416_0014"
down_revision = "20260416_0013"
branch_labels = None
depends_on = None


_INDICATOR_TEMPLATES_TABLE = sa.table(
    "indicator_templates",
    sa.column("tema", sa.String),
    sa.column("indicador", sa.String),
    sa.column("unidade", sa.String),
    sa.column("gri_code", sa.String),
    sa.column("group_key", sa.String),
    sa.column("kind", sa.String),
    sa.column("display_order", sa.Integer),
)


# ---------------------------------------------------------------------------
# v2 catalog — GRI-aligned
# ---------------------------------------------------------------------------
# Schema: (tema, indicador, unidade, gri_code, group_key, kind, display_order)
# kind ∈ {"input", "computed_sum", "computed_pct"}

_CATALOG_V2: list[dict[str, object]] = []


def _add(
    tema: str,
    indicador: str,
    unidade: str,
    gri_code: str | None,
    group_key: str | None,
    kind: str,
) -> None:
    _CATALOG_V2.append(
        {
            "tema": tema,
            "indicador": indicador,
            "unidade": unidade,
            "gri_code": gri_code,
            "group_key": group_key,
            "kind": kind,
            "display_order": len(_CATALOG_V2),
        }
    )


# --- Clima e Energia -------------------------------------------------------
_add(
    "Clima e Energia",
    "Energia consumida — renovável",
    "kWh/ano",
    "GRI 302-1",
    "energy_mix",
    "input",
)
_add(
    "Clima e Energia",
    "Energia consumida — não-renovável",
    "kWh/ano",
    "GRI 302-1",
    "energy_mix",
    "input",
)
_add(
    "Clima e Energia",
    "Consumo total de energia",
    "kWh/ano",
    "GRI 302-1",
    "energy_mix",
    "computed_sum",
)
_add(
    "Clima e Energia",
    "% Energia renovável",
    "%",
    "GRI 302-1",
    "energy_mix",
    "computed_pct",
)
_add(
    "Clima e Energia",
    "Intensidade energética",
    "kWh/unidade produzida",
    "GRI 302-3",
    None,
    "input",
)
_add("Clima e Energia", "Emissões GEE — Escopo 1", "tCO₂e", "GRI 305-1", None, "input")
_add("Clima e Energia", "Emissões GEE — Escopo 2", "tCO₂e", "GRI 305-2", None, "input")
_add("Clima e Energia", "Emissões GEE — Escopo 3", "tCO₂e", "GRI 305-3", None, "input")
_add(
    "Clima e Energia",
    "Meta de redução de GEE",
    "% até 20XX",
    "GRI 305-5",
    None,
    "input",
)

# --- Água ------------------------------------------------------------------
_add(
    "Água",
    "Água captada — superficial",
    "m³/ano",
    "GRI 303-3",
    "water_withdrawal",
    "input",
)
_add(
    "Água",
    "Água captada — subterrânea",
    "m³/ano",
    "GRI 303-3",
    "water_withdrawal",
    "input",
)
_add(
    "Água",
    "Água captada — rede pública",
    "m³/ano",
    "GRI 303-3",
    "water_withdrawal",
    "input",
)
_add(
    "Água",
    "Água captada — água do mar",
    "m³/ano",
    "GRI 303-3",
    "water_withdrawal",
    "input",
)
_add(
    "Água",
    "Água captada — produzida/terceiros",
    "m³/ano",
    "GRI 303-3",
    "water_withdrawal",
    "input",
)
_add(
    "Água",
    "Total captado",
    "m³/ano",
    "GRI 303-3",
    "water_withdrawal",
    "computed_sum",
)
_add("Água", "Água descartada", "m³/ano", "GRI 303-4", None, "input")
_add("Água", "Consumo de água", "m³/ano", "GRI 303-5", None, "input")
_add("Água", "Água reutilizada", "m³/ano", "GRI 303-3", None, "input")
_add(
    "Água",
    "Intensidade hídrica",
    "m³/unidade produzida",
    "GRI 303-5",
    None,
    "input",
)

# --- Resíduos --------------------------------------------------------------
_add(
    "Resíduos",
    "Resíduos — reciclagem",
    "t/ano",
    "GRI 306-4",
    "waste_by_disposal",
    "input",
)
_add(
    "Resíduos",
    "Resíduos — reuso",
    "t/ano",
    "GRI 306-4",
    "waste_by_disposal",
    "input",
)
_add(
    "Resíduos",
    "Resíduos — compostagem",
    "t/ano",
    "GRI 306-4",
    "waste_by_disposal",
    "input",
)
_add(
    "Resíduos",
    "Resíduos — incineração com recuperação",
    "t/ano",
    "GRI 306-4",
    "waste_by_disposal",
    "input",
)
_add(
    "Resíduos",
    "Resíduos — incineração sem recuperação",
    "t/ano",
    "GRI 306-5",
    "waste_by_disposal",
    "input",
)
_add(
    "Resíduos",
    "Resíduos — aterro",
    "t/ano",
    "GRI 306-5",
    "waste_by_disposal",
    "input",
)
_add(
    "Resíduos",
    "Resíduos — outros destinos",
    "t/ano",
    "GRI 306-5",
    "waste_by_disposal",
    "input",
)
_add(
    "Resíduos",
    "Total de resíduos gerados",
    "t/ano",
    "GRI 306-3",
    "waste_by_disposal",
    "computed_sum",
)

# --- Saúde e Segurança do Trabalho ----------------------------------------
_add(
    "Saúde e Segurança do Trabalho",
    "Horas-homem trabalhadas",
    "horas",
    "GRI 403-9",
    None,
    "input",
)
_add(
    "Saúde e Segurança do Trabalho",
    "Acidentes com afastamento",
    "unidades",
    "GRI 403-9",
    None,
    "input",
)
_add(
    "Saúde e Segurança do Trabalho",
    "Dias perdidos por acidentes",
    "dias",
    "GRI 403-9",
    None,
    "input",
)
_add(
    "Saúde e Segurança do Trabalho",
    "Taxa de frequência de acidentes (LTIFR)",
    "índice",
    "GRI 403-9",
    None,
    "input",
)
_add(
    "Saúde e Segurança do Trabalho",
    "Fatalidades relacionadas ao trabalho",
    "unidades",
    "GRI 403-9",
    None,
    "input",
)
_add(
    "Saúde e Segurança do Trabalho",
    "Taxa de fatalidades",
    "por milhão de horas",
    "GRI 403-9",
    None,
    "input",
)

# --- Capital Humano --------------------------------------------------------
_add("Capital Humano", "Total de colaboradores", "unidades", "GRI 2-7", None, "input")

# Novas contratações — por gênero (401-1)
_add(
    "Capital Humano",
    "Novas contratações — mulheres",
    "unidades",
    "GRI 401-1",
    "new_hires_gender",
    "input",
)
_add(
    "Capital Humano",
    "Novas contratações — homens",
    "unidades",
    "GRI 401-1",
    "new_hires_gender",
    "input",
)
_add(
    "Capital Humano",
    "Novas contratações — outros/não declarado",
    "unidades",
    "GRI 401-1",
    "new_hires_gender",
    "input",
)
_add(
    "Capital Humano",
    "Total de novas contratações",
    "unidades",
    "GRI 401-1",
    "new_hires_gender",
    "computed_sum",
)

# Novas contratações — por faixa etária (401-1)
_add(
    "Capital Humano",
    "Novas contratações — < 30 anos",
    "unidades",
    "GRI 401-1",
    "new_hires_age",
    "input",
)
_add(
    "Capital Humano",
    "Novas contratações — 30-50 anos",
    "unidades",
    "GRI 401-1",
    "new_hires_age",
    "input",
)
_add(
    "Capital Humano",
    "Novas contratações — > 50 anos",
    "unidades",
    "GRI 401-1",
    "new_hires_age",
    "input",
)

# Rotatividade (401-1)
_add(
    "Capital Humano",
    "Taxa de rotatividade — total",
    "%",
    "GRI 401-1",
    None,
    "input",
)
_add(
    "Capital Humano",
    "Rotatividade — mulheres",
    "%",
    "GRI 401-1",
    "turnover_gender",
    "input",
)
_add(
    "Capital Humano",
    "Rotatividade — homens",
    "%",
    "GRI 401-1",
    "turnover_gender",
    "input",
)
_add(
    "Capital Humano",
    "Rotatividade — < 30 anos",
    "%",
    "GRI 401-1",
    "turnover_age",
    "input",
)
_add(
    "Capital Humano",
    "Rotatividade — 30-50 anos",
    "%",
    "GRI 401-1",
    "turnover_age",
    "input",
)
_add(
    "Capital Humano",
    "Rotatividade — > 50 anos",
    "%",
    "GRI 401-1",
    "turnover_age",
    "input",
)

# Treinamento (404-1)
_add(
    "Capital Humano",
    "Horas médias de treinamento — mulheres",
    "h/ano",
    "GRI 404-1",
    "training_gender",
    "input",
)
_add(
    "Capital Humano",
    "Horas médias de treinamento — homens",
    "h/ano",
    "GRI 404-1",
    "training_gender",
    "input",
)

# Diversidade (405-1) — por nível × {gênero, faixa etária}
for _level_label, _level_slug in (
    ("Diretoria", "board"),
    ("Gerência", "mgmt"),
    ("Operacional", "ops"),
):
    _add(
        "Capital Humano",
        f"{_level_label} — % mulheres",
        "%",
        "GRI 405-1",
        f"diversity_{_level_slug}_gender",
        "input",
    )
    _add(
        "Capital Humano",
        f"{_level_label} — % homens",
        "%",
        "GRI 405-1",
        f"diversity_{_level_slug}_gender",
        "input",
    )
    _add(
        "Capital Humano",
        f"{_level_label} — % < 30 anos",
        "%",
        "GRI 405-1",
        f"diversity_{_level_slug}_age",
        "input",
    )
    _add(
        "Capital Humano",
        f"{_level_label} — % 30-50 anos",
        "%",
        "GRI 405-1",
        f"diversity_{_level_slug}_age",
        "input",
    )
    _add(
        "Capital Humano",
        f"{_level_label} — % > 50 anos",
        "%",
        "GRI 405-1",
        f"diversity_{_level_slug}_age",
        "input",
    )

# --- Governança / Ética ---------------------------------------------------
_add(
    "Governança / Ética",
    "Número de denúncias recebidas",
    "unidades",
    "GRI 2-26",
    None,
    "input",
)
_add(
    "Governança / Ética",
    "Número de denúncias resolvidas",
    "unidades",
    "GRI 2-26",
    None,
    "input",
)

# --- Desempenho Econômico --------------------------------------------------
_add(
    "Desempenho Econômico",
    "Valor econômico gerado e distribuído",
    "R$ milhões/ano",
    "GRI 201-1",
    None,
    "input",
)


# ---------------------------------------------------------------------------
# Legacy v1 catalog (kept only for downgrade reseed)
# ---------------------------------------------------------------------------


def _v1(tema: str, indicador: str, unidade: str) -> dict[str, str]:
    return {"tema": tema, "indicador": indicador, "unidade": unidade}


_CATALOG_V1 = [
    _v1("Clima e Energia", "Consumo total de energia", "kWh/ano"),
    _v1("Clima e Energia", "Intensidade energética", "kWh/unidade produzida"),
    _v1("Clima e Energia", "Emissões GEE – Scope 1", "tCO₂e"),
    _v1("Clima e Energia", "Emissões GEE – Scope 2", "tCO₂e"),
    _v1("Clima e Energia", "Emissões GEE – Scope 3", "tCO₂e"),
    _v1("Clima e Energia", "Metas de redução de GEE", "% redução até 20XX"),
    _v1("Água", "Consumo total de água", "m³/ano"),
    _v1("Água", "Intensidade hídrica", "m³/unidade produzida"),
    _v1("Água", "Percentual de água reutilizada", "%"),
    _v1("Resíduos", "Total de resíduos gerados", "t/ano"),
    _v1("Resíduos", "Percentual reciclado", "%"),
    _v1("Resíduos", "Percentual destinado ao reuso", "%"),
    _v1("Resíduos", "Percentual destinado ao aterro/incineração", "%"),
    _v1(
        "Saúde e Segurança do Trabalho",
        "Taxa de frequência de acidentes (LTIFR)",
        "índice",
    ),
    _v1("Saúde e Segurança do Trabalho", "Dias perdidos por acidentes", "dias"),
    _v1(
        "Saúde e Segurança do Trabalho",
        "Número de acidentes com afastamento",
        "unidades",
    ),
    _v1(
        "Capital Humano",
        "Média de horas de treinamento por colaborador",
        "h/ano",
    ),
    _v1("Capital Humano", "Percentual de diversidade – Diretoria", "%"),
    _v1("Capital Humano", "Percentual de diversidade – Gerência", "%"),
    _v1("Capital Humano", "Percentual de diversidade – Operacional", "%"),
    _v1("Governança / Ética", "Número de denúncias recebidas", "unidades"),
    _v1("Governança / Ética", "Número de denúncias resolvidas", "unidades"),
    _v1(
        "Desempenho Econômico",
        "Investimentos em projetos sustentáveis (CAPEX/OPEX)",
        "R$ milhões/ano",
    ),
    _v1(
        "Desempenho Econômico",
        "Receita proveniente de produtos/serviços sustentáveis",
        "R$ milhões/ano",
    ),
    _v1(
        "Desempenho Econômico",
        "Valor econômico gerado e distribuído",
        "R$ milhões/ano",
    ),
]


def upgrade() -> None:
    op.add_column(
        "indicator_templates",
        sa.Column("gri_code", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "indicator_templates",
        sa.Column("group_key", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "indicator_templates",
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'input'"),
        ),
    )
    op.add_column(
        "indicator_templates",
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    op.execute(sa.text("DELETE FROM indicator_templates"))
    op.bulk_insert(_INDICATOR_TEMPLATES_TABLE, _CATALOG_V2)


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM indicator_templates"))
    op.bulk_insert(
        sa.table(
            "indicator_templates",
            sa.column("tema", sa.String),
            sa.column("indicador", sa.String),
            sa.column("unidade", sa.String),
        ),
        _CATALOG_V1,
    )
    op.drop_column("indicator_templates", "display_order")
    op.drop_column("indicator_templates", "kind")
    op.drop_column("indicator_templates", "group_key")
    op.drop_column("indicator_templates", "gri_code")
