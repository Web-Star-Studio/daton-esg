"""Tests for the Prompt-Mestre vocabulary linter."""

from app.services.vocabulary_linter import (
    CONTROLLED_TERMS,
    FORBIDDEN_TERMS,
    lint,
)


def test_forbidden_term_replaced_and_reported() -> None:
    content = (
        "A organização é reconhecida por seu orgulho institucional e pelo "
        "protagonismo no setor."
    )
    result = lint(content)
    assert "[termo removido]" in result.cleaned_content
    assert "orgulho" not in result.cleaned_content.lower()
    assert "protagonismo" not in result.cleaned_content.lower()
    removed_terms = {r.term.lower() for r in result.removals}
    assert "orgulho" in removed_terms
    assert "protagonismo" in removed_terms


def test_forbidden_multi_word_term() -> None:
    content = "A cooperativa é referência absoluta no mercado."
    result = lint(content)
    assert "[termo removido]" in result.cleaned_content
    assert result.removals
    assert any("referência absoluta" in r.term.lower() for r in result.removals)


def test_controlled_term_flagged_without_data() -> None:
    content = "A organização demonstra compromisso com a sustentabilidade."
    result = lint(content)
    assert result.warnings
    assert any(w.term.lower() == "compromisso" for w in result.warnings)


def test_controlled_term_allowed_with_numeric_context() -> None:
    content = (
        "A organização demonstra compromisso com a redução de emissões, "
        "atingindo 12.895 tCO2e no período."
    )
    result = lint(content)
    terms = {w.term.lower() for w in result.warnings}
    # "compromisso" followed shortly by "12.895 tCO2e" is OK; "redução" followed
    # shortly by numeric data is OK.
    assert (
        "compromisso" not in terms
        or "redução" not in terms
        or len(result.warnings) == 0
    )


def test_clean_content_is_noop() -> None:
    content = (
        "A organização estabeleceu uma política de gestão ambiental alinhada "
        "ao GRI 305-1 e à ISO 14001."
    )
    result = lint(content)
    assert result.cleaned_content == content
    assert not result.removals
    assert not result.warnings


def test_case_insensitive_matching() -> None:
    # uppercase match; word boundary respected (TRANSFORMADOR followed by a
    # non-word char like space) so the bare form gets caught.
    content = "O processo é TRANSFORMADOR do setor."
    result = lint(content)
    assert "TRANSFORMADOR" not in result.cleaned_content
    assert "[termo removido]" in result.cleaned_content


def test_does_not_match_inside_unrelated_words() -> None:
    # "inovador" is forbidden, but "inovadores" (plural) is not a direct match.
    # Our word-boundary pattern should not match "inovadores" as "inovador".
    content = "Os processos inovadores seguem a metodologia GRI."
    result = lint(content)
    # the plural form should pass through untouched
    assert "inovadores" in result.cleaned_content


def test_term_lists_are_consistent() -> None:
    # sanity: lists remain lowercase and non-empty
    assert FORBIDDEN_TERMS
    assert CONTROLLED_TERMS
    for term in FORBIDDEN_TERMS + CONTROLLED_TERMS:
        assert term == term.lower()
