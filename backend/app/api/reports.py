"""Report CRUD + SSE streaming endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.schemas.report import (
    ReportListItem,
    ReportResponse,
    ReportSectionUpdateRequest,
)
from app.services.project_service import get_project_for_user
from app.services.report_service import (
    create_report,
    export_report_docx,
    get_report_detail,
    list_reports,
    stream_report_generation,
    update_report_section,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/reports", tags=["reports"])


@router.get("", response_model=list[ReportListItem])
async def list_project_reports(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReportListItem]:
    project = await get_project_for_user(session, project_id, current_user.id)
    reports = await list_reports(session, project_id=project.id)
    return [ReportListItem.model_validate(report) for report in reports]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    project_id: UUID,
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    report = await get_report_detail(
        session, project_id=project.id, report_id=report_id
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    return ReportResponse.model_validate(report)


@router.post("/generate")
async def generate_report(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    material_topics = project.material_topics
    if not isinstance(material_topics, list) or len(material_topics) == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Selecione ao menos um tema material em Materialidade & ODS "
                "antes de gerar o relatório."
            ),
        )
    try:
        report = await create_report(session, project_id=project.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    stream = stream_report_generation(
        session, project=project, report=report
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{report_id}/export/docx")
async def export_docx(
    project_id: UUID,
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    project = await get_project_for_user(session, project_id, current_user.id)
    report = await get_report_detail(
        session, project_id=project.id, report_id=report_id
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    try:
        download_url = await export_report_docx(
            session, project=project, report=report
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"download_url": download_url}


@router.patch(
    "/{report_id}/sections/{section_key}",
    response_model=ReportResponse,
)
async def patch_report_section(
    project_id: UUID,
    report_id: UUID,
    section_key: str,
    payload: ReportSectionUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    try:
        report = await update_report_section(
            session,
            project_id=project.id,
            report_id=report_id,
            section_key=section_key,
            new_content=payload.content,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail="Seção não encontrada no relatório.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReportResponse.model_validate(report)
