from pydantic import BaseModel, ConfigDict


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


class CaptacaoRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sessao: str
    tipo_dado: str
    gri_code: str | None
    descricao: str
    fonte_documental: str
    tipo_evidencia: str
