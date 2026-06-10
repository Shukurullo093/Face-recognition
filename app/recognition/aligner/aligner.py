"""5-point face alignment to the canonical 112x112 ArcFace template.

Uses a similarity transform (rotation + uniform scale + translation) estimated
from the 5 facial landmarks to the standard ArcFace reference points. This is
the exact preprocessing ArcFace models were trained with.
"""
from __future__ import annotations

import cv2
import numpy as np
from skimage import transform as sk_transform

# Canonical 5-point template for 112x112 aligned faces (ArcFace / InsightFace).
ARCFACE_REFERENCE_LANDMARKS = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)

OUTPUT_SIZE = 112


class FaceAligner:
    """Warps a detected face to the 112x112 aligned crop ArcFace expects."""

    def __init__(self, output_size: int = OUTPUT_SIZE) -> None:
        self.output_size = output_size
        # Scale the reference template if a non-default size is requested.
        if output_size == OUTPUT_SIZE:
            self.reference = ARCFACE_REFERENCE_LANDMARKS
        else:
            self.reference = ARCFACE_REFERENCE_LANDMARKS * (output_size / OUTPUT_SIZE)

    def align(self, image_bgr: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        """Return a (output_size, output_size, 3) BGR aligned face crop.

        Args:
            image_bgr: source BGR image.
            landmarks: (5, 2) landmark coordinates in source-image space.
        """
        if landmarks.shape != (5, 2):
            raise ValueError(f"Expected (5,2) landmarks, got {landmarks.shape}")

        tform = sk_transform.SimilarityTransform()
        tform.estimate(landmarks.astype(np.float32), self.reference)
        matrix = tform.params[0:2, :]
        aligned = cv2.warpAffine(
            image_bgr,
            matrix,
            (self.output_size, self.output_size),
            borderValue=0.0,
        )
        return aligned
