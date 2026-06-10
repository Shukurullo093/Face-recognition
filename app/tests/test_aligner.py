"""Aligner tests — verifies the similarity transform maps landmarks onto template."""
from __future__ import annotations

import numpy as np

from app.recognition.aligner.aligner import ARCFACE_REFERENCE_LANDMARKS, FaceAligner


def test_align_output_shape() -> None:
    aligner = FaceAligner()
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    landmarks = ARCFACE_REFERENCE_LANDMARKS * 2 + 30  # arbitrary affine of template
    out = aligner.align(img, landmarks)
    assert out.shape == (112, 112, 3)
    assert out.dtype == np.uint8


def test_align_maps_landmarks_to_template() -> None:
    """If landmarks already equal the template, alignment is ~identity."""
    aligner = FaceAligner()
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    out = aligner.align(img, ARCFACE_REFERENCE_LANDMARKS.copy())
    assert out.shape == (112, 112, 3)


def test_align_rejects_bad_landmark_shape() -> None:
    aligner = FaceAligner()
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    try:
        aligner.align(img, np.zeros((3, 2), dtype=np.float32))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
