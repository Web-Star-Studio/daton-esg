from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndicatorTemplate(Base):
    """Seed reference data for the ESG indicator library (Indicadores ESG sheet).

    Not a runtime project indicator — this is the menu of indicators a
    consultant can select from when populating project-level data.

    Columns introduced in the v2 catalog:
      - `gri_code`: GRI disclosure code this indicator maps to (nullable for free-form).
      - `group_key`: groups sibling inputs together (e.g. `waste_by_disposal`).
        Inputs sharing a `group_key` are rendered together; the UI derives
        totals/percentages from them when a sibling has `kind != 'input'`.
      - `kind`: one of `input`, `computed_sum`, `computed_pct`. Only `input`
        rows accept user values and get persisted.
      - `display_order`: ordering hint within a `tema`/`group_key`.
    """

    __tablename__ = "indicator_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tema: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    indicador: Mapped[str] = mapped_column(String(255), nullable=False)
    unidade: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    gri_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    group_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="input")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
