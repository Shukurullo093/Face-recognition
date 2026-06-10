"""ArcFace-r100 embedding extractor (ONNX Runtime).

Input : 112x112 aligned BGR face crop(s).
Output: 512-D FP32 embedding(s), L2-normalised so that the dot product of two
        embeddings equals their cosine similarity.
"""
from __future__ import annotations

import cv2
import numpy as np
import onnxruntime as ort

from app.core.logging import get_logger

log = get_logger(__name__)

EMBEDDING_DIM = 512
INPUT_SIZE = 112


class ArcFaceEmbedder:
    """ONNX Runtime ArcFace wrapper supporting batched inference."""

    def __init__(self, model_path: str, providers: list[str]) -> None:
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # Some ArcFace exports declare a fixed output batch of 1; batched inference
        # still returns the correct (N, 512). Severity 3 hides that benign warning.
        so.log_severity_level = 3
        self.session = ort.InferenceSession(model_path, sess_options=so, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        out_shape = self.session.get_outputs()[0].shape
        self.dim = int(out_shape[-1]) if isinstance(out_shape[-1], int) else EMBEDDING_DIM
        log.info(
            "arcface_loaded",
            model=model_path,
            providers=self.session.get_providers(),
            dim=self.dim,
        )

    @staticmethod
    def _preprocess(faces_bgr: list[np.ndarray]) -> np.ndarray:
        """Stack aligned crops into an NCHW blob: RGB, (x-127.5)/127.5."""
        blob = cv2.dnn.blobFromImages(
            faces_bgr,
            scalefactor=1.0 / 127.5,
            size=(INPUT_SIZE, INPUT_SIZE),
            mean=(127.5, 127.5, 127.5),
            swapRB=True,
        )
        return blob

    @staticmethod
    def _l2_normalize(emb: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(emb, axis=1, keepdims=True)
        norm = np.clip(norm, a_min=1e-12, a_max=None)
        return emb / norm

    def embed(self, aligned_face_bgr: np.ndarray) -> np.ndarray:
        """Single aligned face -> (512,) normalised float32 embedding."""
        return self.embed_batch([aligned_face_bgr])[0]

    def embed_batch(self, aligned_faces_bgr: list[np.ndarray]) -> np.ndarray:
        """Batch of aligned faces -> (N, 512) normalised float32 embeddings."""
        if not aligned_faces_bgr:
            return np.empty((0, self.dim), dtype=np.float32)
        blob = self._preprocess(aligned_faces_bgr)
        embeddings = self.session.run([self.output_name], {self.input_name: blob})[0]
        embeddings = np.asarray(embeddings, dtype=np.float32)
        return self._l2_normalize(embeddings)
