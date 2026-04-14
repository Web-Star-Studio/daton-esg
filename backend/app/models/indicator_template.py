from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndicatorTemplate(Base):
    """Seed reference data for the ESG indicator library (Indicadores ESG sheet).

    Not a runtime project indicator — this is the menu of indicators a
    consultant can select from when populating project-level data.
    """

    __tablename__ = "indicator_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tema: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    indicador: Mapped[str] = mapped_column(String(255), nullable=False)
    unidade: Mapped[str] = mapped_column(String(64), nullable=False, default="")
