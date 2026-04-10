from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.models.enums import ClassificationConfidence, ExtractionReviewStatus
from app.schemas import (
    ClassificationRebuildResponse,
    DocumentExtractionResponse,
    DocumentExtractionUpdateRequest,
    ProjectResponse,
)
from app.services.data_extraction_service import (
    get_data_extraction_for_project,
    list_data_extractions_for_project,
    rebuild_project_classification,
    update_data_extraction_review,
    validate_project_classification,
)
from app.services.project_service import get_project_for_user

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["project-data"])


@router.get("/data-extractions", response_model=list[DocumentExtractionResponse])
async def list_project_data_extractions(
    project_id: UUID,
    document_id: UUID | None = Query(default=None),
    category: str | None = Query(default=None),
    confidence: ClassificationConfidence | None = Query(default=None),
    review_status: ExtractionReviewStatus | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[DocumentExtractionResponse]:
    project = await get_project_for_user(session, project_id, current_user.id)
    extractions = await list_data_extractions_for_project(
        session,
        project_id=project.id,
        document_id=document_id,
        category=category,
        confidence=confidence,
        review_status=review_status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [
        DocumentExtractionResponse.model_validate(extraction)
        for extraction in extractions
    ]


@router.patch(
    "/data-extractions/{extraction_id}",
    response_model=DocumentExtractionResponse,
)
async def patch_project_data_extraction(
    project_id: UUID,
    extraction_id: UUID,
    payload: DocumentExtractionUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentExtractionResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    extraction = await get_data_extraction_for_project(
        session,
        project_id=project.id,
        extraction_id=extraction_id,
    )
    updated_extraction = await update_data_extraction_review(
        session,
        extraction=extraction,
        project=project,
        reviewer=current_user,
        corrected_value=payload.corrected_value,
        corrected_unit=payload.corrected_unit,
        corrected_period=payload.corrected_period,
        corrected_esg_category=payload.corrected_esg_category,
        review_status=payload.review_status,
        correction_reason=payload.correction_reason,
    )
    return DocumentExtractionResponse.model_validate(updated_extraction)


@router.post("/classification/rebuild", response_model=ClassificationRebuildResponse)
async def rebuild_project_classification_endpoint(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClassificationRebuildResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    documents_processed, extractions_created = await rebuild_project_classification(
        session,
        project=project,
    )
    return ClassificationRebuildResponse(
        documents_processed=documents_processed,
        extractions_created=extractions_created,
    )


@router.post("/classification/validate", response_model=ProjectResponse)
async def validate_project_classification_endpoint(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    validated_project = await validate_project_classification(
        session,
        project=project,
    )
    return ProjectResponse.model_validate(validated_project)
