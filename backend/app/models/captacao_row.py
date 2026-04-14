from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CaptacaoRow(Base):
    """Seed reference data for the Matriz de Captação — maps each ESG session
    (document directory key) to the types of evidence consultants must collect,
    with the corresponding GRI code suggestion.

    `sessao` uses the existing document_directories.DOCUMENT_DIRECTORIES keys.
    `gri_code` is a text reference (not a real FK) to gri_standards.code; some
    rows have no GRI code assigned.
    """

    __tablename__ = "captacao_matriz"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sessao: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tipo_dado: Mapped[str] = mapped_column(String(255), nullable=False)
    gri_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False, default="")
    fonte_documental: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tipo_evidencia: Mapped[str] = mapped_column(String(128), nullable=False, default="")
