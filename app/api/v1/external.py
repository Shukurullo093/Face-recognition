"""3rd-party (API-key authenticated) 1:N identification endpoint.

Returns at most the single best match above the recognition threshold; if no
face is detected or nothing clears the threshold, `matched` is false.
Per-key rate limiting is enforced inside the `get_api_key` dependency.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.api.deps import ExternalRecognitionServiceDep
from app.core.exceptions import InvalidImageError
from app.schemas.api_key import ExternalSearchResponse

router = APIRouter(prefix="/external", tags=["external"])

_MAX_IMAGE_BYTES = 15 * 1024 * 1024


@router.post(
    "/search",
    response_model=ExternalSearchResponse,
    summary="1:N identify — top-1 match for 3rd-party callers (X-API-Key)",
)
async def external_search(
    service: ExternalRecognitionServiceDep,
    image: Annotated[UploadFile, File()],
) -> ExternalSearchResponse:
    if image.content_type and not image.content_type.startswith("image/"):
        raise InvalidImageError(f"Unsupported content type: {image.content_type}")
    data = await image.read()
    if not data:
        raise InvalidImageError("Empty image upload")
    if len(data) > _MAX_IMAGE_BYTES:
        raise InvalidImageError("Image exceeds 15 MB limit")
    return await service.identify_top1(data)
