"""Shared test fixtures. Tests avoid GPU/DB by using fakes and env flags."""
from __future__ import annotations

import os

import numpy as np
import pytest

# Ensure settings load without a real .env and skip heavy model loading.
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long")
os.environ.setdefault("FR_SKIP_MODELS", "1")

from app.recognition.types import DetectedFace, FaceResult  # noqa: E402


class FakeDetector:
    """Returns a configurable list of detections without any model."""

    def __init__(self, faces: list[DetectedFace]) -> None:
        self._faces = faces

    def detect(self, image_bgr: np.ndarray, max_num: int = 0) -> list[DetectedFace]:
        faces = list(self._faces)
        return faces[:max_num] if max_num > 0 else faces


class FakeAligner:
    def align(self, image_bgr: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        return np.zeros((112, 112, 3), dtype=np.uint8)


class FakeEmbedder:
    """Deterministic embeddings derived from the detection score."""

    def embed(self, aligned_face_bgr: np.ndarray) -> np.ndarray:
        return self.embed_batch([aligned_face_bgr])[0]

    def embed_batch(self, faces: list[np.ndarray]) -> np.ndarray:
        out = np.tile(np.arange(512, dtype=np.float32), (len(faces), 1))
        norm = np.linalg.norm(out, axis=1, keepdims=True)
        return out / norm


def make_face(score: float = 0.99, size: float = 100.0) -> DetectedFace:
    return DetectedFace(
        bbox=np.array([10, 10, 10 + size, 10 + size], dtype=np.float32),
        score=score,
        landmarks=np.array(
            [[38, 51], [73, 51], [56, 71], [41, 92], [70, 92]], dtype=np.float32
        ),
    )


@pytest.fixture
def detected_face() -> DetectedFace:
    return make_face()


@pytest.fixture
def face_result(detected_face: DetectedFace) -> FaceResult:
    emb = np.arange(512, dtype=np.float32)
    return FaceResult(detection=detected_face, embedding=emb / np.linalg.norm(emb))
