"""Cosine similarity helpers.

The heavy 1:N search runs inside PostgreSQL via the pgvector HNSW index (see
FaceRepository). These helpers are used for 1:1 verification and unit tests,
where embeddings are already in memory.
"""
from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors (handles unnormalised input)."""
    a = a.ravel().astype(np.float32)
    b = b.ravel().astype(np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def cosine_similarity_matrix(query: np.ndarray, gallery: np.ndarray) -> np.ndarray:
    """Cosine similarity of one query (512,) against a gallery (N, 512).

    Returns a (N,) array. Inputs need not be normalised.
    """
    query = query.ravel().astype(np.float32)
    gallery = np.atleast_2d(gallery).astype(np.float32)
    q_norm = np.linalg.norm(query)
    g_norm = np.linalg.norm(gallery, axis=1)
    denom = np.clip(q_norm * g_norm, a_min=1e-12, a_max=None)
    return (gallery @ query) / denom
