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
    Response,
    UploadFile,
    status,
)

import base64

import numpy as np

from app.api.deps import (
    BulkImportServiceDep,
    DBDep,
    RecognitionServiceDep,
    require_admin,
    require_operator,
    require_viewer,
)
from app.core.exceptions import EntityNotFoundError, InvalidImageError
from app.repositories.face_repo import FaceRepository
from app.schemas.face import (
    FaceGalleryItem,
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


@router.get(
    "",
    response_model=list[FaceGalleryItem],
    dependencies=[Depends(require_viewer)],
    summary="List enrolled faces with thumbnails and embeddings (gallery)",
)
async def list_faces(
    db: DBDep,
    limit: Annotated[int, Query(ge=1, le=60)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
    person_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[FaceGalleryItem]:
    rows = await FaceRepository(db).list_with_person(
        limit=limit, offset=offset, person_id=person_id
    )
    items: list[FaceGalleryItem] = []
    for face, full_name in rows:
        emb = [float(x) for x in face.embedding]
        thumb = (
            "data:image/jpeg;base64," + base64.b64encode(face.thumbnail).decode()
            if face.thumbnail
            else None
        )
        items.append(
            FaceGalleryItem(
                id=face.id,
                person_id=face.person_id,
                full_name=full_name,
                det_score=face.det_score,
                quality=face.quality,
                image_path=face.image_path,
                created_at=face.created_at,
                thumbnail=thumb,
                embedding=emb,
                embedding_dim=len(emb),
                embedding_norm=round(float(np.linalg.norm(emb)), 6),
            )
        )
    return items


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
    "/enroll",
    response_model=FaceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_operator)],
    summary="Enroll a face by person name (find-or-create) — used by client folder import",
)
async def enroll_by_name(
    service: RecognitionServiceDep,
    person_name: Annotated[str, Form()],
    image: Annotated[UploadFile, File()],
) -> FaceRegisterResponse:
    data = await _read_image(image)
    return await service.register_by_name(person_name, data, image_path=image.filename)


@router.put(
    "/{face_id}/image",
    response_model=FaceRegisterResponse,
    dependencies=[Depends(require_operator)],
    summary="Replace a face's image (re-detects & re-embeds, keeps face_id)",
)
async def replace_face_image(
    service: RecognitionServiceDep,
    face_id: uuid.UUID,
    image: Annotated[UploadFile, File()],
) -> FaceRegisterResponse:
    data = await _read_image(image)
    return await service.replace_face_image(face_id, data, image_path=image.filename)


@router.delete(
    "/{face_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[Depends(require_operator)],
    summary="Delete a single enrolled face",
)
async def delete_face(face_id: uuid.UUID, db: DBDep) -> None:
    repo = FaceRepository(db)
    face = await repo.get(face_id)
    if face is None:
        raise EntityNotFoundError(f"Face {face_id} not found")
    await repo.delete(face)


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
