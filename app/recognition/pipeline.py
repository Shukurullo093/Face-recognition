"""RecognitionPipeline — composes detector + aligner + embedder.

This is the single entry point the service layer uses. It is constructed once
at startup (models are heavy) and shared. ONNX Runtime inference is blocking
CPU/GPU work, so the async wrappers offload to a thread via asyncio.to_thread,
keeping the event loop responsive.
"""
from __future__ import annotations

import asyncio

import cv2
import numpy as np

from app.core.config import Settings
from app.core.exceptions import (
    InvalidImageError,
    LowQualityFaceError,
    MultipleFacesError,
    NoFaceDetectedError,
)
from app.core.logging import get_logger
from app.recognition.aligner import FaceAligner
from app.recognition.arcface import ArcFaceEmbedder
from app.recognition.detector import BaseDetector, SCRFDetector
from app.recognition.types import DetectedFace, FaceResult

log = get_logger(__name__)


class RecognitionPipeline:
    """End-to-end: bytes/ndarray -> detect -> align -> embed."""

    def __init__(
        self,
        detector: BaseDetector,
        aligner: FaceAligner,
        embedder: ArcFaceEmbedder,
        min_face_size: int,
    ) -> None:
        self.detector = detector
        self.aligner = aligner
        self.embedder = embedder
        self.min_face_size = min_face_size

    # ---------- factory ----------
    @classmethod
    def from_settings(cls, settings: Settings) -> "RecognitionPipeline":
        providers = settings.onnx_providers_list
        detector = SCRFDetector(
            model_path=settings.DETECTOR_MODEL_PATH,
            providers=providers,
            det_threshold=settings.DETECTION_THRESHOLD,
            nms_threshold=settings.DETECTION_NMS_THRESHOLD,
            input_size=settings.DETECTION_INPUT_SIZE,
        )
        embedder = ArcFaceEmbedder(
            model_path=settings.ARCFACE_MODEL_PATH,
            providers=providers,
        )
        return cls(detector, FaceAligner(), embedder, settings.MIN_FACE_SIZE)

    # ---------- helpers ----------
    @staticmethod
    def decode_image(data: bytes) -> np.ndarray:
        """Decode raw image bytes into a BGR ndarray."""
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise InvalidImageError("Could not decode image bytes")
        return img

    def _check_quality(self, face: DetectedFace) -> None:
        if min(face.width, face.height) < self.min_face_size:
            raise LowQualityFaceError(
                f"Face too small ({face.width:.0f}x{face.height:.0f}px); "
                f"minimum is {self.min_face_size}px"
            )

    # ---------- sync core (runs in worker thread) ----------
    def _process_single(self, image_bgr: np.ndarray) -> FaceResult:
        faces = self.detector.detect(image_bgr, max_num=0)
        if not faces:
            raise NoFaceDetectedError("No face detected in image")
        if len(faces) > 1:
            raise MultipleFacesError(
                f"{len(faces)} faces detected; enrollment/verification needs exactly one",
                detail={"face_count": len(faces)},
            )
        face = faces[0]
        self._check_quality(face)
        aligned = self.aligner.align(image_bgr, face.landmarks)
        embedding = self.embedder.embed(aligned)
        return FaceResult(detection=face, embedding=embedding)

    def _process_largest(self, image_bgr: np.ndarray) -> FaceResult:
        """For search: tolerate multiple faces, pick the most prominent one."""
        faces = self.detector.detect(image_bgr, max_num=1)
        if not faces:
            raise NoFaceDetectedError("No face detected in image")
        face = faces[0]
        self._check_quality(face)
        aligned = self.aligner.align(image_bgr, face.landmarks)
        embedding = self.embedder.embed(aligned)
        return FaceResult(detection=face, embedding=embedding)

    def _process_all(self, image_bgr: np.ndarray) -> list[FaceResult]:
        faces = self.detector.detect(image_bgr, max_num=0)
        if not faces:
            return []
        valid = [f for f in faces if min(f.width, f.height) >= self.min_face_size]
        if not valid:
            return []
        aligned = [self.aligner.align(image_bgr, f.landmarks) for f in valid]
        embeddings = self.embedder.embed_batch(aligned)
        return [FaceResult(detection=f, embedding=embeddings[i]) for i, f in enumerate(valid)]

    # ---------- async public API ----------
    async def process_single(self, image_bgr: np.ndarray) -> FaceResult:
        """Detect & embed exactly one face (raises if 0 or >1)."""
        return await asyncio.to_thread(self._process_single, image_bgr)

    async def process_largest(self, image_bgr: np.ndarray) -> FaceResult:
        """Detect & embed the single most prominent face."""
        return await asyncio.to_thread(self._process_largest, image_bgr)

    async def process_all(self, image_bgr: np.ndarray) -> list[FaceResult]:
        """Detect & embed all valid faces (batched)."""
        return await asyncio.to_thread(self._process_all, image_bgr)
