from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    pass


class OdsGoal(Base):
    """Seed reference data for the 17 UN Sustainable Development Goals."""

    __tablename__ = "ods_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ods_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    objetivo: Mapped[str] = mapped_column(String(255), nullable=False)

    metas: Mapped[list["OdsMeta"]] = relationship(
        "OdsMeta",
        back_populates="ods",
        cascade="all, delete-orphan",
        order_by="OdsMeta.meta_code",
    )


class OdsMeta(Base):
    """Seed reference data for the 169 ODS targets (metas)."""

    __tablename__ = "ods_metas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ods_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ods_goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meta_code: Mapped[str] = mapped_column(String(10), nullable=False)
    meta_text: Mapped[str] = mapped_column(Text, nullable=False)

    ods: Mapped["OdsGoal"] = relationship("OdsGoal", back_populates="metas")
