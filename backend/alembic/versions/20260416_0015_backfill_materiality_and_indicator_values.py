"""backfill legacy project.material_topics and project.indicator_values

Two schema tightenings landed alongside the indicator catalog v2:

1. `MaterialTopic.pillar` narrowed from `Literal["E","S","G"]` to `Literal["E","S"]`
   and `priority` moved from `int (1..5)` to `Literal["alta","media","baixa"]`.
2. The indicator catalog was rewritten (new names, group keys, derived rows),
   so a handful of v1 `indicator_values.indicador` strings were renamed.

Without a data migration, legacy rows would either 422 on subsequent updates
or be silently filtered out by the normalizer on the next UI save — both
paths lose work. This migration rewrites the JSONB columns in place so they
match the new schema before any read path re-validates them.
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa

from alembic import op

revision = "20260416_0015"
down_revision = "20260416_0014"
branch_labels = None
depends_on = None


_PRIORITY_INT_MAP: dict[int, str] = {
    1: "baixa",
    2: "baixa",
    3: "media",
    4: "alta",
    5: "alta",
}

_VALID_PRIORITIES: set[str] = {"alta", "media", "baixa"}

# Legacy v1 → v2 indicator renames. Only direct 1:1 renames are listed;
# entries that no longer exist in v2 (e.g. "Percentual reciclado", which was
# replaced by absolute-value rows under `waste_by_disposal`) are left
# untouched — the UI will surface them as orphaned values and the consultant
# can re-enter them under the new catalog.
_INDICATOR_NAME_MAP: dict[str, str] = {
    "Emissões GEE – Scope 1": "Emissões GEE — Escopo 1",
    "Emissões GEE – Scope 2": "Emissões GEE — Escopo 2",
    "Emissões GEE – Scope 3": "Emissões GEE — Escopo 3",
    "Metas de redução de GEE": "Meta de redução de GEE",
    "Número de acidentes com afastamento": "Acidentes com afastamento",
}


def _normalize_material_topics(raw: Any) -> tuple[list[dict[str, Any]] | None, bool]:
    """Return (new_list, changed). new_list is None when raw is not a list."""
    if not isinstance(raw, list):
        return None, False
    out: list[dict[str, Any]] = []
    changed = False
    for item in raw:
        if not isinstance(item, dict):
            changed = True
            continue
        pillar = item.get("pillar")
        topic = item.get("topic")
        priority = item.get("priority")
        if not isinstance(topic, str) or not topic.strip():
            changed = True
            continue
        if pillar == "G":
            pillar = "S"
            changed = True
        elif pillar not in ("E", "S"):
            changed = True
            continue
        if isinstance(priority, bool):
            changed = True
            continue
        if isinstance(priority, int):
            mapped = _PRIORITY_INT_MAP.get(priority)
            if mapped is None:
                changed = True
                continue
            priority = mapped
            changed = True
        elif priority not in _VALID_PRIORITIES:
            changed = True
            continue
        out.append(
            {
                "pillar": pillar,
                "topic": topic.strip(),
                "priority": priority,
            }
        )
    return out, changed


def _normalize_indicator_values(raw: Any) -> tuple[list[dict[str, Any]] | None, bool]:
    if not isinstance(raw, list):
        return None, False
    out: list[dict[str, Any]] = []
    changed = False
    for item in raw:
        if not isinstance(item, dict):
            changed = True
            continue
        indicador = item.get("indicador")
        if isinstance(indicador, str):
            renamed = _INDICATOR_NAME_MAP.get(indicador)
            if renamed is not None and renamed != indicador:
                item = {**item, "indicador": renamed}
                changed = True
        out.append(item)
    return out, changed


def upgrade() -> None:
    connection = op.get_bind()
    rows = (
        connection.execute(
            sa.text("SELECT id, material_topics, indicator_values FROM projects")
        )
        .mappings()
        .all()
    )
    for row in rows:
        updates: dict[str, str] = {}
        new_topics, topics_changed = _normalize_material_topics(row["material_topics"])
        if topics_changed:
            updates["material_topics"] = json.dumps(new_topics)
        new_values, values_changed = _normalize_indicator_values(
            row["indicator_values"]
        )
        if values_changed:
            updates["indicator_values"] = json.dumps(new_values)
        if not updates:
            continue
        params: dict[str, Any] = {"id": row["id"]}
        set_clauses: list[str] = []
        for col, val in updates.items():
            set_clauses.append(f"{col} = CAST(:{col} AS JSONB)")
            params[col] = val
        connection.execute(
            sa.text(f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = :id"),
            params,
        )


def downgrade() -> None:
    # One-way data cleanup (G-pillar topics and int priorities cannot be
    # restored from normalized values without losing fidelity). No-op.
    pass
