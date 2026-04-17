"""Read-only endpoints exposing seeded ESG reference data (GRI, ODS,
indicators, captação matriz) to the frontend pickers.

All endpoints require authentication (same as the rest of the API) but return
global reference data — not per-project."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import CaptacaoRow, GriStandard, IndicatorTemplate, OdsGoal, User
from app.schemas.reference_data import (
    CaptacaoRowResponse,
    GriStandardResponse,
    IndicatorTemplateResponse,
    OdsGoalResponse,
)

router = APIRouter(prefix="/api/v1/reference", tags=["reference"])


@router.get("/gri-standards", response_model=list[GriStandardResponse])
async def list_gri_standards(
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[GriStandardResponse]:
    result = await session.execute(
        select(GriStandard).order_by(GriStandard.family, GriStandard.code)
    )
    return [GriStandardResponse.model_validate(row) for row in result.scalars()]


@router.get("/ods-goals", response_model=list[OdsGoalResponse])
async def list_ods_goals(
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[OdsGoalResponse]:
    result = await session.execute(
        select(OdsGoal)
        .options(selectinload(OdsGoal.metas))
        .order_by(OdsGoal.ods_number)
    )
    return [OdsGoalResponse.model_validate(row) for row in result.scalars()]


@router.get("/indicator-templates", response_model=list[IndicatorTemplateResponse])
async def list_indicator_templates(
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[IndicatorTemplateResponse]:
    result = await session.execute(
        select(IndicatorTemplate).order_by(
            IndicatorTemplate.tema,
            IndicatorTemplate.display_order,
            IndicatorTemplate.indicador,
        )
    )
    return [IndicatorTemplateResponse.model_validate(row) for row in result.scalars()]


@router.get("/captacao-matriz", response_model=list[CaptacaoRowResponse])
async def list_captacao_matriz(
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[CaptacaoRowResponse]:
    result = await session.execute(
        select(CaptacaoRow).order_by(CaptacaoRow.sessao, CaptacaoRow.tipo_dado)
    )
    return [CaptacaoRowResponse.model_validate(row) for row in result.scalars()]
