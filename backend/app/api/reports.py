"""Report CRUD + SSE streaming endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.models.enums import ReportStatus
from app.schemas.report import (
    GenerateReportRequest,
    ReportListItem,
    ReportResponse,
    ReportSectionUpdateRequest,
)
from app.services.project_service import get_project_for_user
from app.services.report_service import (
    ReportConflictError,
    create_report,
    delete_report,
    export_report_docx,
    get_report_detail,
    list_reports,
    stream_report_generation,
    stream_section_regeneration,
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


@router.delete("/{report_id}", status_code=204)
async def delete_report_endpoint(
    project_id: UUID,
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    project = await get_project_for_user(session, project_id, current_user.id)
    try:
        await delete_report(session, project_id=project.id, report_id=report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReportConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post("/generate")
async def generate_report(
    project_id: UUID,
    payload: GenerateReportRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Generate a report. If payload.section_keys is provided, only those
    sections are produced. Otherwise all 14 sections run."""
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
    except (ReportConflictError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    section_keys = None
    if payload and payload.section_keys:
        section_keys = set(payload.section_keys)

    stream = stream_report_generation(
        session,
        project=project,
        report=report,
        section_keys=section_keys,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{report_id}/sections/{section_key}/generate")
async def regenerate_section(
    project_id: UUID,
    report_id: UUID,
    section_key: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Regenerate a single section of an existing DRAFT report."""
    project = await get_project_for_user(session, project_id, current_user.id)
    report = await get_report_detail(
        session, project_id=project.id, report_id=report_id
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    if report.status == ReportStatus.GENERATING:
        raise HTTPException(
            status_code=409,
            detail="Relatório em geração — aguarde a conclusão.",
        )
    stream = stream_section_regeneration(
        session,
        project=project,
        report=report,
        section_key=section_key,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{report_id}/export/docx")
async def export_docx(
    project_id: UUID,
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Generate the DOCX, upload to S3, return a presigned download URL."""
    project = await get_project_for_user(session, project_id, current_user.id)
    report = await get_report_detail(
        session, project_id=project.id, report_id=report_id
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    try:
        download_url = await export_report_docx(session, project=project, report=report)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return {"download_url": download_url}


@router.get("/{report_id}/export/docx")
async def get_export_docx_url(
    project_id: UUID,
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | None]:
    """Return the existing export URL if available, without side effects."""
    project = await get_project_for_user(session, project_id, current_user.id)
    report = await get_report_detail(
        session, project_id=project.id, report_id=report_id
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    return {"download_url": report.exported_docx_s3}


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
    except ReportConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReportResponse.model_validate(report)
