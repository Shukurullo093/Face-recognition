"""Pipeline orchestration tests using fakes (no ONNX, no GPU)."""
from __future__ import annotations

import numpy as np
import pytest

from app.core.exceptions import MultipleFacesError, NoFaceDetectedError
from app.recognition.pipeline import RecognitionPipeline
from app.tests.conftest import FakeAligner, FakeDetector, FakeEmbedder, make_face

IMG = np.zeros((200, 200, 3), dtype=np.uint8)


def _pipeline(faces: list) -> RecognitionPipeline:
    return RecognitionPipeline(
        detector=FakeDetector(faces),
        aligner=FakeAligner(),
        embedder=FakeEmbedder(),
        min_face_size=40,
    )


async def test_process_single_success() -> None:
    pipe = _pipeline([make_face(score=0.97)])
    result = await pipe.process_single(IMG)
    assert result.detection.score == pytest.approx(0.97)
    assert result.embedding.shape == (512,)
    assert np.linalg.norm(result.embedding) == pytest.approx(1.0, abs=1e-5)


async def test_process_single_no_face_raises() -> None:
    pipe = _pipeline([])
    with pytest.raises(NoFaceDetectedError):
        await pipe.process_single(IMG)


async def test_process_single_multiple_faces_raises() -> None:
    pipe = _pipeline([make_face(), make_face()])
    with pytest.raises(MultipleFacesError):
        await pipe.process_single(IMG)


async def test_process_largest_tolerates_multiple() -> None:
    pipe = _pipeline([make_face(score=0.9), make_face(score=0.8)])
    result = await pipe.process_largest(IMG)
    assert result.detection.score == pytest.approx(0.9)


async def test_process_all_batches() -> None:
    pipe = _pipeline([make_face(), make_face(), make_face()])
    results = await pipe.process_all(IMG)
    assert len(results) == 3


async def test_decode_invalid_image_raises() -> None:
    from app.core.exceptions import InvalidImageError

    pipe = _pipeline([])
    with pytest.raises(InvalidImageError):
        pipe.decode_image(b"not-an-image")
