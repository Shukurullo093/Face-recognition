"""Shared value objects for the recognition pipeline."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class DetectedFace:
    """One detected face: bbox (x1,y1,x2,y2), detection score, 5 landmarks (5x2)."""

    bbox: np.ndarray  # shape (4,), float32
    score: float
    landmarks: np.ndarray  # shape (5, 2), float32

    @property
    def area(self) -> float:
        return float((self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1]))

    @property
    def width(self) -> float:
        return float(self.bbox[2] - self.bbox[0])

    @property
    def height(self) -> float:
        return float(self.bbox[3] - self.bbox[1])


@dataclass(slots=True)
class FaceResult:
    """Full result for a single face: detection + 512-D normalised embedding."""

    detection: DetectedFace
    embedding: np.ndarray  # shape (512,), float32, L2-normalised
