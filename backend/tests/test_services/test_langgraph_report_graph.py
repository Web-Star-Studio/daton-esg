"""Deterministic tests for the LangGraph report pipeline helpers.

LLM and DB integration are exercised via a separate end-to-end smoke test
(not included here) to keep this suite fast and self-contained.
"""

from __future__ import annotations

from app.services.langgraph_report_graph import (
    _dispatcher_router,
    _extract_gri_evidence,
    _extract_inline_gri_codes,
    _has_enquadramento_block,
    _render_sumario_markdown,
    _strip_invalid_gri_parentheticals,
    _summarize_section_for_prior,
)
from app.services.report_sections import REPORT_SECTIONS, get_section

# ---- helpers ----


def test_extract_inline_gri_codes_dedup_and_valid_only() -> None:
    content = (
        "Consumo de energia (GRI 302-1) e intensidade (GRI 302-3). "
        "Retomando (GRI 302-1) e (GRI 999-1) inexistente."
    )
    valid = {"GRI 302-1", "GRI 302-3"}
    assert _extract_inline_gri_codes(content, valid) == ["GRI 302-1", "GRI 302-3"]


def test_strip_invalid_gri_parentheticals() -> None:
    content = "Escopo 1 (GRI 305-1). E também (GRI 999-99) não existe."
    valid = {"GRI 305-1"}
    cleaned, invalid = _strip_invalid_gri_parentheticals(content, valid)
    assert "(GRI 999-99)" not in cleaned
    assert "(GRI 305-1)" in cleaned
    assert "GRI 999-99" in invalid


def test_enquadramento_block_detection() -> None:
    ok = "Texto da seção.\n\nEnquadramento ESG e normativo\n- Pilares ESG: E"
    missing = "Texto da seção sem o bloco final."
    assert _has_enquadramento_block(ok) is True
    assert _has_enquadramento_block(missing) is False


def test_extract_gri_evidence_captures_surrounding_text() -> None:
    content = (
        "A organização monitora emissões diretas (GRI 305-1) com base em "
        "inventário GHG Protocol."
    )
    valid = {"GRI 305-1"}
    entries = _extract_gri_evidence(content, "gestao-ambiental", valid)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["code"] == "GRI 305-1"
    assert entry["section_key"] == "gestao-ambiental"
    assert "emissões" in entry["excerpt"].lower()


def test_summarize_section_for_prior_truncates_long_content() -> None:
    long_content = "Parágrafo. " * 200
    section = {
        "key": "x",
        "title": "Exemplo",
        "content": long_content,
        "gri_codes_used": ["GRI 2-1"],
    }
    summary = _summarize_section_for_prior(section, max_len=80)
    assert len(summary) < 250
    assert "Exemplo" in summary
    assert "GRI 2-1" in summary


def test_render_sumario_markdown_groups_by_family() -> None:
    rows = [
        {
            "code": "GRI 2-1",
            "family": "2",
            "standard_text": "Detalhes",
            "evidence_excerpt": "foo",
            "section_ref": "a-empresa",
            "status": "atendido",
            "found_in_text": True,
        },
        {
            "code": "GRI 305-1",
            "family": "300",
            "standard_text": "Escopo 1",
            "evidence_excerpt": None,
            "section_ref": None,
            "status": "nao_atendido",
            "found_in_text": False,
        },
    ]
    md = _render_sumario_markdown(rows)
    assert "### GRI 2" in md
    assert "### GRI 300" in md
    assert "GRI 2-1" in md
    assert "GRI 305-1" in md
    assert "atendido" in md


# ---- section manifest ----


def test_report_sections_have_unique_keys_and_orders() -> None:
    keys = [s.key for s in REPORT_SECTIONS]
    orders = [s.order for s in REPORT_SECTIONS]
    assert len(set(keys)) == len(keys)
    assert len(set(orders)) == len(orders)
    assert len(REPORT_SECTIONS) >= 10  # vertical slice target


def test_report_sections_reference_valid_directory_keys() -> None:
    from app.services.document_directories import DOCUMENT_DIRECTORY_BY_KEY

    for section in REPORT_SECTIONS:
        for directory_key in section.directory_keys:
            assert directory_key in DOCUMENT_DIRECTORY_BY_KEY, (
                f"{section.key} references unknown directory {directory_key}"
            )


def test_report_section_target_words_in_range() -> None:
    for section in REPORT_SECTIONS:
        assert 500 <= section.target_words <= 5000, (
            f"{section.key} target_words {section.target_words} out of range"
        )


def test_get_section_lookup() -> None:
    assert get_section("a-empresa") is not None
    assert get_section("no-such-section") is None


def test_sumario_gri_section_exists_and_uses_gri_summary_strategy() -> None:
    sumario = get_section("sumario-gri")
    assert sumario is not None
    assert sumario.prompt_strategy == "gri_summary"
    assert sumario.order == max(s.order for s in REPORT_SECTIONS)


# ---- dispatcher routing ----


class _StubTemplate:
    def __init__(self, strategy: str) -> None:
        self.prompt_strategy = strategy


def test_dispatcher_router_generate() -> None:
    state = {
        "current_section_index": 0,
        "section_templates": [_StubTemplate("narrative")],
    }
    assert _dispatcher_router(state) == "generate"  # type: ignore[arg-type]


def test_dispatcher_router_gri_summary() -> None:
    state = {
        "current_section_index": 0,
        "section_templates": [_StubTemplate("gri_summary")],
    }
    assert _dispatcher_router(state) == "gri_summary"  # type: ignore[arg-type]


def test_dispatcher_router_done_when_index_exhausted() -> None:
    state = {
        "current_section_index": 3,
        "section_templates": [_StubTemplate("narrative")] * 3,
    }
    assert _dispatcher_router(state) == "done"  # type: ignore[arg-type]
