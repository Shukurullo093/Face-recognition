"""Unit tests for SCRFD decode helpers (no model / GPU needed)."""
from __future__ import annotations

import numpy as np
import pytest

from app.recognition.detector.scrfd import _distance2bbox, _distance2kps, _nms


def test_distance2bbox_decodes_ltrb() -> None:
    points = np.array([[50.0, 50.0]], dtype=np.float32)
    distance = np.array([[10.0, 20.0, 30.0, 40.0]], dtype=np.float32)  # l, t, r, b
    box = _distance2bbox(points, distance)
    assert box[0].tolist() == [40.0, 30.0, 80.0, 90.0]


def test_distance2kps_decodes_five_points() -> None:
    points = np.array([[10.0, 10.0]], dtype=np.float32)
    distance = np.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]], dtype=np.float32)
    kps = _distance2kps(points, distance)
    assert kps.shape == (1, 10)
    assert kps[0, 0] == 11.0 and kps[0, 1] == 12.0  # first landmark


def test_nms_suppresses_overlapping_boxes() -> None:
    dets = np.array(
        [
            [10, 10, 50, 50, 0.9],   # keep
            [12, 12, 52, 52, 0.8],   # heavy overlap -> suppressed
            [100, 100, 140, 140, 0.7],  # disjoint -> keep
        ],
        dtype=np.float32,
    )
    keep = _nms(dets, thresh=0.4)
    assert keep == [0, 2]


def test_nms_keeps_all_when_disjoint() -> None:
    dets = np.array(
        [[0, 0, 10, 10, 0.9], [100, 100, 110, 110, 0.8]], dtype=np.float32
    )
    assert sorted(_nms(dets, thresh=0.4)) == [0, 1]


@pytest.mark.parametrize("thresh", [0.0, 0.5, 1.0])
def test_nms_runs_for_thresholds(thresh: float) -> None:
    dets = np.array([[0, 0, 10, 10, 0.9]], dtype=np.float32)
    assert _nms(dets, thresh) == [0]
