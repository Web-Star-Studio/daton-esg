from typing import Literal

from pydantic import BaseModel, ConfigDict

IndicatorTemplateKind = Literal["input", "computed_sum", "computed_pct"]


class GriStandardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    family: str
    standard_text: str


class OdsMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meta_code: str
    meta_text: str


class OdsGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ods_number: int
    objetivo: str
    metas: list[OdsMetaResponse]


class IndicatorTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tema: str
    indicador: str
    unidade: str
    gri_code: str | None = None
    group_key: str | None = None
    kind: IndicatorTemplateKind = "input"
    display_order: int = 0


class CaptacaoRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sessao: str
    tipo_dado: str
    gri_code: str | None
    descricao: str
    fonte_documental: str
    tipo_evidencia: str
