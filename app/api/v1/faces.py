"""Face recognition endpoints: register, verify (1:1), search (1:N), bulk import."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)

from app.api.deps import (
    BulkImportServiceDep,
    RecognitionServiceDep,
    require_admin,
    require_operator,
    require_viewer,
)
from app.core.exceptions import EntityNotFoundError, InvalidImageError
from app.schemas.face import (
    FaceRegisterResponse,
    ImportJobStatus,
    ImportRequest,
    SearchResponse,
    VerifyResponse,
)
from app.services.job_store import job_store

router = APIRouter(prefix="/faces", tags=["faces"])

_MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15 MB upload guard


async def _read_image(file: UploadFile) -> bytes:
    if file.content_type and not file.content_type.startswith("image/"):
        raise InvalidImageError(f"Unsupported content type: {file.content_type}")
    data = await file.read()
    if not data:
        raise InvalidImageError("Empty image upload")
    if len(data) > _MAX_IMAGE_BYTES:
        raise InvalidImageError("Image exceeds 15 MB limit")
    return data


@router.post(
    "/register",
    response_model=FaceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_operator)],
    summary="Enroll a face for a person",
)
async def register_face(
    service: RecognitionServiceDep,
    person_id: Annotated[uuid.UUID, Form()],
    image: Annotated[UploadFile, File()],
) -> FaceRegisterResponse:
    data = await _read_image(image)
    return await service.register(person_id, data, image_path=image.filename)


@router.post(
    "/verify",
    response_model=VerifyResponse,
    dependencies=[Depends(require_viewer)],
    summary="1:1 verification against a known person",
)
async def verify_face(
    service: RecognitionServiceDep,
    person_id: Annotated[uuid.UUID, Form()],
    image: Annotated[UploadFile, File()],
) -> VerifyResponse:
    data = await _read_image(image)
    return await service.verify(person_id, data)


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_viewer)],
    summary="1:N identification across the whole gallery",
)
async def search_faces(
    service: RecognitionServiceDep,
    image: Annotated[UploadFile, File()],
    top_k: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> SearchResponse:
    data = await _read_image(image)
    return await service.search(data, top_k=top_k)


@router.post(
    "/import",
    response_model=ImportJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
    summary="Start a background bulk import from a server-side folder",
)
async def bulk_import(
    payload: ImportRequest,
    background: BackgroundTasks,
    service: BulkImportServiceDep,
) -> ImportJobStatus:
    job = job_store.create()
    background.add_task(service.run, job, payload.root_path)
    return ImportJobStatus(
        job_id=job.job_id,
        state=job.state,
        total=job.total,
        processed=job.processed,
        succeeded=job.succeeded,
        failed=job.failed,
    )


@router.get(
    "/import/{job_id}",
    response_model=ImportJobStatus,
    dependencies=[Depends(require_admin)],
    summary="Poll bulk-import progress",
)
async def import_status(job_id: uuid.UUID) -> ImportJobStatus:
    job = job_store.get(job_id)
    if job is None:
        raise EntityNotFoundError(f"Import job {job_id} not found")
    return ImportJobStatus(
        job_id=job.job_id,
        state=job.state,
        total=job.total,
        processed=job.processed,
        succeeded=job.succeeded,
        failed=job.failed,
        errors=job.errors,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
