"""Tests for the extraction service: conflict detection + apply (upsert) logic.

These tests do not exercise the LLM path. They validate the deterministic
helpers that:
  * compute conflict_with_existing against project state
  * upsert into Project.material_topics / sdg_goals / indicator_values without
    duplicating identities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models import Project
from app.models.enums import (
    ExtractionConfidence,
    ExtractionTargetKind,
    ProjectStatus,
)
from app.services.extraction.orchestrator import compute_conflict
from app.services.extraction_service import (
    _project_apply_indicator_value,
    _project_apply_material_topic,
    _project_apply_sdg,
)


def make_project() -> Project:
    return Project(
        id=uuid4(),
        user_id=uuid4(),
        org_name="Acme",
        base_year=2025,
        status=ProjectStatus.COLLECTING,
        material_topics=[],
        sdg_goals=[],
        indicator_values=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# compute_conflict
# ---------------------------------------------------------------------------


def test_compute_conflict_no_conflict_when_topic_absent() -> None:
    project = make_project()
    project.material_topics = [
        {"pillar": "S", "topic": "GRI 401-1", "priority": "alta"}
    ]
    conflict, snapshot = compute_conflict(
        ExtractionTargetKind.MATERIAL_TOPIC,
        {"pillar": "E", "topic": "GRI 305-1", "priority": "media"},
        project,
    )
    assert conflict is False
    assert snapshot is None


def test_compute_conflict_detects_topic_match_by_pillar_and_topic() -> None:
    project = make_project()
    existing = {"pillar": "E", "topic": "GRI 305-1", "priority": "alta"}
    project.material_topics = [existing]
    conflict, snapshot = compute_conflict(
        ExtractionTargetKind.MATERIAL_TOPIC,
        {"pillar": "E", "topic": "GRI 305-1", "priority": "media"},
        project,
    )
    assert conflict is True
    assert snapshot == existing


def test_compute_conflict_detects_indicator_value_by_full_identity() -> None:
    project = make_project()
    existing = {
        "tema": "Clima e Energia",
        "indicador": "Energia consumida — renovável",
        "unidade": "kWh/ano",
        "value": "100",
    }
    project.indicator_values = [existing]
    conflict, snapshot = compute_conflict(
        ExtractionTargetKind.INDICATOR_VALUE,
        {
            "tema": "Clima e Energia",
            "indicador": "Energia consumida — renovável",
            "unidade": "kWh/ano",
            "value": "999",
        },
        project,
    )
    assert conflict is True
    assert snapshot == existing


def test_compute_conflict_indicator_no_match_when_unit_differs() -> None:
    project = make_project()
    project.indicator_values = [
        {
            "tema": "Clima e Energia",
            "indicador": "Energia consumida — renovável",
            "unidade": "kWh/ano",
            "value": "100",
        }
    ]
    conflict, snapshot = compute_conflict(
        ExtractionTargetKind.INDICATOR_VALUE,
        {
            "tema": "Clima e Energia",
            "indicador": "Energia consumida — renovável",
            "unidade": "MWh/ano",
            "value": "100",
        },
        project,
    )
    assert conflict is False
    assert snapshot is None


def test_compute_conflict_sdg_match_by_number() -> None:
    project = make_project()
    project.sdg_goals = [{"ods_number": 7, "objetivo": "Energia limpa"}]
    conflict, snapshot = compute_conflict(
        ExtractionTargetKind.SDG_GOAL,
        {"ods_number": 7, "objetivo": "Energia"},
        project,
    )
    assert conflict is True
    assert snapshot is not None and snapshot["ods_number"] == 7


# ---------------------------------------------------------------------------
# upsert helpers
# ---------------------------------------------------------------------------


def test_apply_material_topic_appends_when_new() -> None:
    project = make_project()
    project.material_topics = [
        {"pillar": "S", "topic": "GRI 401-1", "priority": "alta"}
    ]
    _project_apply_material_topic(
        project, {"pillar": "E", "topic": "GRI 305-1", "priority": "media"}
    )
    assert len(project.material_topics) == 2
    pillars = [t["pillar"] for t in project.material_topics]
    assert pillars == ["S", "E"]


def test_apply_material_topic_replaces_when_identity_matches() -> None:
    project = make_project()
    project.material_topics = [
        {"pillar": "E", "topic": "GRI 305-1", "priority": "alta"}
    ]
    _project_apply_material_topic(
        project, {"pillar": "E", "topic": "GRI 305-1", "priority": "baixa"}
    )
    assert len(project.material_topics) == 1
    assert project.material_topics[0]["priority"] == "baixa"


def test_apply_indicator_value_replaces_only_same_unit() -> None:
    project = make_project()
    project.indicator_values = [
        {
            "tema": "Clima e Energia",
            "indicador": "Energia consumida — renovável",
            "unidade": "kWh/ano",
            "value": "100",
        }
    ]
    # Same identity → replace
    _project_apply_indicator_value(
        project,
        {
            "tema": "Clima e Energia",
            "indicador": "Energia consumida — renovável",
            "unidade": "kWh/ano",
            "value": "200",
        },
    )
    assert len(project.indicator_values) == 1
    assert project.indicator_values[0]["value"] == "200"

    # Different unit → append (not a conflict)
    _project_apply_indicator_value(
        project,
        {
            "tema": "Clima e Energia",
            "indicador": "Energia consumida — renovável",
            "unidade": "MWh/ano",
            "value": "0.5",
        },
    )
    assert len(project.indicator_values) == 2


def test_apply_sdg_replaces_when_number_matches() -> None:
    project = make_project()
    project.sdg_goals = [
        {"ods_number": 7, "objetivo": "Antigo", "acao": "x"}
    ]
    _project_apply_sdg(
        project,
        {"ods_number": 7, "objetivo": "Energia limpa e acessível", "acao": ""},
    )
    assert len(project.sdg_goals) == 1
    assert project.sdg_goals[0]["objetivo"] == "Energia limpa e acessível"
