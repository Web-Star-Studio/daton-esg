"""Structural tests for the v2 indicator catalog embedded in the 0014 migration.

These tests protect against regressions in the GRI-aligned catalog reseed
without requiring a live database.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260416_0014_indicator_catalog_v2.py"
)


@pytest.fixture(scope="module")
def migration_module():
    spec = importlib.util.spec_from_file_location(
        "indicator_catalog_v2_migration", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v2_catalog_non_empty(migration_module) -> None:
    catalog = migration_module._CATALOG_V2
    assert len(catalog) > 30


def test_v2_catalog_rows_have_required_fields(migration_module) -> None:
    for row in migration_module._CATALOG_V2:
        assert row["tema"].strip()
        assert row["indicador"].strip()
        assert row["kind"] in {"input", "computed_sum", "computed_pct"}
        assert isinstance(row["display_order"], int)


def test_v2_catalog_indicadores_unique(migration_module) -> None:
    names = [row["indicador"] for row in migration_module._CATALOG_V2]
    assert len(set(names)) == len(names), "indicador names must be unique"


def test_v2_catalog_display_order_is_dense(migration_module) -> None:
    orders = sorted(row["display_order"] for row in migration_module._CATALOG_V2)
    assert orders == list(range(len(orders)))


def test_v2_catalog_gri_codes_are_well_formed(migration_module) -> None:
    for row in migration_module._CATALOG_V2:
        code = row.get("gri_code")
        if code is None:
            continue
        assert code.startswith("GRI "), f"gri_code {code!r} must start with 'GRI '"


def test_v2_catalog_removes_non_gri_economic_indicators(migration_module) -> None:
    names = {row["indicador"] for row in migration_module._CATALOG_V2}
    for removed in (
        "Investimentos em projetos sustentáveis (CAPEX/OPEX)",
        "Receita proveniente de produtos/serviços sustentáveis",
    ):
        assert removed not in names


def test_v2_catalog_includes_required_gri_disclosures(migration_module) -> None:
    names = {row["indicador"] for row in migration_module._CATALOG_V2}
    expected = {
        "Energia consumida — renovável",
        "Energia consumida — não-renovável",
        "Água captada — superficial",
        "Água descartada",
        "Consumo de água",
        "Resíduos — reciclagem",
        "Resíduos — aterro",
        "Fatalidades relacionadas ao trabalho",
        "Novas contratações — mulheres",
        "Novas contratações — < 30 anos",
        "Diretoria — % mulheres",
        "Valor econômico gerado e distribuído",
    }
    missing = expected - names
    assert not missing, f"missing required indicators: {missing}"


def test_v2_catalog_computed_rows_share_group_with_inputs(migration_module) -> None:
    by_group: dict[str, list[dict]] = {}
    for row in migration_module._CATALOG_V2:
        group_key = row.get("group_key")
        if group_key is None:
            continue
        by_group.setdefault(group_key, []).append(row)

    for group_key, rows in by_group.items():
        kinds = {r["kind"] for r in rows}
        if "computed_sum" in kinds or "computed_pct" in kinds:
            assert "input" in kinds, (
                f"group {group_key!r} has computed rows but no input siblings"
            )
