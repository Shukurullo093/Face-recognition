"""Cosine similarity unit tests."""
from __future__ import annotations

import numpy as np
import pytest

from app.recognition.search.similarity import cosine_similarity, cosine_similarity_matrix


def test_identical_vectors_similarity_is_one() -> None:
    v = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)


def test_orthogonal_vectors_similarity_is_zero() -> None:
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


def test_opposite_vectors_similarity_is_minus_one() -> None:
    a = np.array([1.0, 1.0], dtype=np.float32)
    assert cosine_similarity(a, -a) == pytest.approx(-1.0, abs=1e-6)


def test_zero_vector_is_safe() -> None:
    a = np.zeros(4, dtype=np.float32)
    b = np.ones(4, dtype=np.float32)
    assert cosine_similarity(a, b) == 0.0


def test_matrix_matches_pairwise() -> None:
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    gallery = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]], dtype=np.float32)
    sims = cosine_similarity_matrix(query, gallery)
    assert sims == pytest.approx([1.0, 0.0, -1.0], abs=1e-6)
