"""Static tests for the reference data migration literals.

These tests validate the seed data structure embedded in
``alembic/versions/20260413_0010_seed_reference_data.py`` without requiring a
live database. They protect against regressions when the source XLSX is
re-extracted.
"""

import importlib.util
import re
from pathlib import Path

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260413_0010_seed_reference_data.py"
)

DOCUMENT_DIRECTORY_KEYS = {
    "visao-estrategica-de-sustentabilidade",
    "governanca-corporativa",
    "gestao-ambiental",
    "desempenho-social",
    "gestao-de-desempenho-economico",
    "relacionamento-com-stakeholders",
    "inovacao-e-desenvolvimento-tecnologico",
    "relatorios-e-normas",
    "comunicacao-e-transparencia",
    "auditorias-e-avaliacoes",
}


@pytest.fixture(scope="module")
def migration_module():
    spec = importlib.util.spec_from_file_location("seed_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gri_standards_count(migration_module) -> None:
    assert len(migration_module.GRI_STANDARDS) == 119


def test_gri_codes_unique(migration_module) -> None:
    codes = [row["code"] for row in migration_module.GRI_STANDARDS]
    assert len(set(codes)) == len(codes)


def test_gri_code_format(migration_module) -> None:
    pattern = re.compile(r"^GRI \d+-\d+[a-z]?$")
    for row in migration_module.GRI_STANDARDS:
        assert pattern.match(row["code"]), f"bad code format: {row['code']}"


def test_gri_family_values(migration_module) -> None:
    families = {row["family"] for row in migration_module.GRI_STANDARDS}
    assert families <= {"2", "3", "200", "300", "400"}


def test_ods_goals_count(migration_module) -> None:
    assert len(migration_module.ODS_GOALS) == 17
    numbers = {row["ods_number"] for row in migration_module.ODS_GOALS}
    assert numbers == set(range(1, 18))


def test_ods_metas_count_and_link(migration_module) -> None:
    assert len(migration_module.ODS_METAS) == 169
    known_ods = {row["ods_number"] for row in migration_module.ODS_GOALS}
    for row in migration_module.ODS_METAS:
        assert row["ods_number"] in known_ods


def test_captacao_rows_count(migration_module) -> None:
    assert len(migration_module.CAPTACAO_ROWS) == 28


def test_captacao_sessions_use_document_directory_keys(migration_module) -> None:
    for row in migration_module.CAPTACAO_ROWS:
        assert row["sessao"] in DOCUMENT_DIRECTORY_KEYS, (
            f"sessao {row['sessao']!r} not in known document directory keys"
        )


def test_captacao_gri_codes_resolve_to_known_standards(migration_module) -> None:
    known_codes = {row["code"] for row in migration_module.GRI_STANDARDS}
    for row in migration_module.CAPTACAO_ROWS:
        code = row["gri_code"]
        if code is None:
            continue
        assert code in known_codes, f"captacao row references unknown GRI code: {code}"


def test_indicator_templates_count(migration_module) -> None:
    assert len(migration_module.INDICATOR_TEMPLATES) == 25


def test_indicator_templates_have_tema_and_indicador(migration_module) -> None:
    for row in migration_module.INDICATOR_TEMPLATES:
        assert row["tema"].strip()
        assert row["indicador"].strip()
