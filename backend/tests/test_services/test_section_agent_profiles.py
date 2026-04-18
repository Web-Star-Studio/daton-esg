"""Tests for section agent profiles and system prompt composition."""

from app.services.prompts import PROMPT_MESTRE
from app.services.report_sections import REPORT_SECTIONS
from app.services.section_agent_profiles import (
    SECTION_AGENT_PROFILES,
    build_agent_system_prompt,
)
from app.services.vocabulary_linter import FORBIDDEN_TERMS


def test_every_section_key_has_a_profile() -> None:
    section_keys = {s.key for s in REPORT_SECTIONS}
    profile_keys = set(SECTION_AGENT_PROFILES.keys())
    assert section_keys == profile_keys, (
        f"Missing profiles: {section_keys - profile_keys}; "
        f"Extra profiles: {profile_keys - section_keys}"
    )


def test_build_agent_system_prompt_starts_with_prompt_mestre() -> None:
    for key, profile in SECTION_AGENT_PROFILES.items():
        prompt = build_agent_system_prompt(profile)
        assert prompt.startswith(PROMPT_MESTRE), (
            f"Profile {key}: system prompt does not start with Prompt-Mestre"
        )


def test_build_agent_system_prompt_contains_agent_identity() -> None:
    for key, profile in SECTION_AGENT_PROFILES.items():
        prompt = build_agent_system_prompt(profile)
        assert profile.agent_name in prompt, f"{key}: agent_name missing"
        assert profile.role_description in prompt, f"{key}: role missing"
        assert "ADENDO DO AGENTE ESPECIALIZADO" in prompt, (
            f"{key}: addendum header missing"
        )


def test_addenda_contain_no_forbidden_terms() -> None:
    for key, profile in SECTION_AGENT_PROFILES.items():
        full_addendum = (
            profile.domain_addendum
            + " "
            + profile.output_structure_hint
            + " "
            + profile.style_nuance
        ).lower()
        for term in FORBIDDEN_TERMS:
            assert term not in full_addendum, (
                f"Profile {key}: forbidden term '{term}' found in addendum"
            )


def test_profiles_have_nonempty_required_fields() -> None:
    for key, profile in SECTION_AGENT_PROFILES.items():
        assert profile.agent_name.strip(), f"{key}: empty agent_name"
        assert profile.role_description.strip(), f"{key}: empty role_description"
        assert profile.domain_addendum.strip(), f"{key}: empty domain_addendum"
        assert profile.output_structure_hint.strip(), (
            f"{key}: empty output_structure_hint"
        )
        assert profile.style_nuance.strip(), f"{key}: empty style_nuance"


def test_prompt_length_is_reasonable() -> None:
    for key, profile in SECTION_AGENT_PROFILES.items():
        prompt = build_agent_system_prompt(profile)
        word_count = len(prompt.split())
        # Prompt-Mestre alone is ~600 words; addenda add 50-200 more.
        assert 500 < word_count < 1200, (
            f"Profile {key}: prompt has {word_count} words — out of expected range"
        )


NARRATIVE_SECTIONS = frozenset(
    {
        "a-empresa",
        "visao-estrategia",
        "governanca",
        "stakeholders",
        "inovacao",
        "auditorias",
        "comunicacao",
        "temas-materiais",
        "alinhamento-ods",
    }
)
QUANTITATIVE_SECTIONS = frozenset(
    {
        "gestao-ambiental",
        "desempenho-social",
        "desempenho-economico",
        "plano-acao",
        "sumario-gri",
    }
)


def test_narrative_sections_have_temperature_override() -> None:
    for key in NARRATIVE_SECTIONS:
        profile = SECTION_AGENT_PROFILES[key]
        assert profile.temperature_override == 0.2, (
            f"Profile {key}: expected temperature_override=0.2, "
            f"got {profile.temperature_override}"
        )


def test_quantitative_sections_have_no_temperature_override() -> None:
    for key in QUANTITATIVE_SECTIONS:
        profile = SECTION_AGENT_PROFILES[key]
        assert profile.temperature_override is None, (
            f"Profile {key}: expected temperature_override=None "
            f"(inherits global), got {profile.temperature_override}"
        )


def test_temperature_override_partition_covers_all_profiles() -> None:
    assert NARRATIVE_SECTIONS.isdisjoint(QUANTITATIVE_SECTIONS)
    assert NARRATIVE_SECTIONS | QUANTITATIVE_SECTIONS == set(
        SECTION_AGENT_PROFILES.keys()
    )
