"""Detector abstraction (DIP) — services depend on this, not on SCRFD directly."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from app.recognition.types import DetectedFace


class BaseDetector(ABC):
    """Interface every face detector must implement."""

    @abstractmethod
    def detect(self, image_bgr: np.ndarray, max_num: int = 0) -> list[DetectedFace]:
        """Detect faces in a BGR (H,W,3) uint8 image.

        Args:
            image_bgr: OpenCV BGR image.
            max_num: keep at most N faces (0 = all). Largest/most central first.

        Returns:
            List of DetectedFace, sorted by descending priority.
        """
        raise NotImplementedError
