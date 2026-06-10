"""Dashboard analytics schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from app.models.recognition_log import RecognitionAction
from app.schemas.common import ORMModel


class StatsResponse(ORMModel):
    total_persons: int
    total_faces: int
    total_events: int
    successful_events: int
    match_rate: float  # successful / total events, in [0, 1]


class LogRead(ORMModel):
    id: uuid.UUID
    action: RecognitionAction
    person_id: uuid.UUID | None
    matched_face_id: uuid.UUID | None
    similarity: float | None
    success: bool
    user_id: str | None
    client_ip: str | None
    message: str | None
    created_at: datetime
