from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GriStandard(Base):
    """Seed reference data for the GRI 2021 standards (Índice GRI)."""

    __tablename__ = "gri_standards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    family: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    standard_text: Mapped[str] = mapped_column(Text, nullable=False)
