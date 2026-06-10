"""SCRFD-2.5GF face detector (ONNX Runtime).

Post-processing follows the official InsightFace SCRFD decode: 3 FPN levels with
strides (8, 16, 32), 2 anchors per location, distance-to-bbox/keypoint decoding,
score thresholding and NMS. Supports both *_kps (with landmarks) and plain
variants, and dynamic or fixed input shapes.

References: https://github.com/deepinsight/insightface/tree/master/detection/scrfd
"""
from __future__ import annotations

import cv2
import numpy as np
import onnxruntime as ort

from app.core.logging import get_logger
from app.recognition.detector.base import BaseDetector
from app.recognition.types import DetectedFace

log = get_logger(__name__)


def _distance2bbox(points: np.ndarray, distance: np.ndarray) -> np.ndarray:
    """Decode (l, t, r, b) distances from anchor centers into (x1,y1,x2,y2)."""
    x1 = points[:, 0] - distance[:, 0]
    y1 = points[:, 1] - distance[:, 1]
    x2 = points[:, 0] + distance[:, 2]
    y2 = points[:, 1] + distance[:, 3]
    return np.stack([x1, y1, x2, y2], axis=-1)


def _distance2kps(points: np.ndarray, distance: np.ndarray) -> np.ndarray:
    """Decode 5 keypoint offsets relative to anchor centers."""
    preds = []
    for i in range(0, distance.shape[1], 2):
        px = points[:, 0] + distance[:, i]
        py = points[:, 1] + distance[:, i + 1]
        preds.append(px)
        preds.append(py)
    return np.stack(preds, axis=-1)


def _nms(dets: np.ndarray, thresh: float) -> list[int]:
    """Standard greedy NMS. `dets` is (N,5): x1,y1,x2,y2,score (score-sorted desc)."""
    x1, y1, x2, y2, scores = dets[:, 0], dets[:, 1], dets[:, 2], dets[:, 3], dets[:, 4]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]
    return keep


class SCRFDetector(BaseDetector):
    """ONNX Runtime SCRFD wrapper. Thread-safe for inference (session is stateless)."""

    def __init__(
        self,
        model_path: str,
        providers: list[str],
        det_threshold: float = 0.5,
        nms_threshold: float = 0.4,
        input_size: int = 640,
    ) -> None:
        self.det_threshold = det_threshold
        self.nms_threshold = nms_threshold
        self.input_size = (input_size, input_size)
        self._center_cache: dict[tuple[int, int, int], np.ndarray] = {}

        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.log_severity_level = 3  # errors only — silence benign batch-shape warnings
        self.session = ort.InferenceSession(model_path, sess_options=so, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]
        log.info(
            "scrfd_loaded",
            model=model_path,
            providers=self.session.get_providers(),
            num_outputs=len(self.output_names),
        )
        self._init_anchor_config(len(self.output_names))

    def _init_anchor_config(self, num_outputs: int) -> None:
        """Infer FPN config from output count (6 = no kps, 9 = with kps)."""
        self.fmc = 3
        self.feat_stride_fpn = [8, 16, 32]
        self.num_anchors = 2
        if num_outputs == 6:
            self.use_kps = False
        elif num_outputs == 9:
            self.use_kps = True
        else:  # fall back to single-anchor configs (rare SCRFD exports)
            self.fmc = num_outputs // (3 if num_outputs in (15,) else 2)
            self.use_kps = num_outputs >= 9
            self.num_anchors = 1
        log.info("scrfd_config", fmc=self.fmc, use_kps=self.use_kps, anchors=self.num_anchors)

    # -- forward over a single padded square image --
    def _forward(
        self, det_img: np.ndarray, threshold: float
    ) -> tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]:
        blob = cv2.dnn.blobFromImage(
            det_img,
            scalefactor=1.0 / 128.0,
            size=self.input_size,
            mean=(127.5, 127.5, 127.5),
            swapRB=True,
        )
        net_outs = self.session.run(self.output_names, {self.input_name: blob})

        input_h, input_w = blob.shape[2], blob.shape[3]
        scores_list, bboxes_list, kpss_list = [], [], []

        for idx, stride in enumerate(self.feat_stride_fpn):
            scores = net_outs[idx]
            bbox_preds = net_outs[idx + self.fmc] * stride
            height, width = input_h // stride, input_w // stride
            key = (height, width, stride)

            if key in self._center_cache:
                anchor_centers = self._center_cache[key]
            else:
                grid = np.stack(np.mgrid[:height, :width][::-1], axis=-1).astype(np.float32)
                anchor_centers = (grid * stride).reshape(-1, 2)
                if self.num_anchors > 1:
                    anchor_centers = np.stack(
                        [anchor_centers] * self.num_anchors, axis=1
                    ).reshape(-1, 2)
                if len(self._center_cache) < 100:
                    self._center_cache[key] = anchor_centers

            # Keep scores as a (k, 1) column so vstack -> (total, 1) and the
            # later hstack with bboxes (total, 4) yields a clean (total, 5).
            scores = scores.reshape(-1, 1)
            pos_inds = np.where(scores.ravel() >= threshold)[0]
            bboxes = _distance2bbox(anchor_centers, bbox_preds)
            scores_list.append(scores[pos_inds])
            bboxes_list.append(bboxes[pos_inds])

            if self.use_kps:
                kps_preds = net_outs[idx + self.fmc * 2] * stride
                kpss = _distance2kps(anchor_centers, kps_preds).reshape(-1, 5, 2)
                kpss_list.append(kpss[pos_inds])

        return scores_list, bboxes_list, kpss_list

    def detect(self, image_bgr: np.ndarray, max_num: int = 0) -> list[DetectedFace]:
        if image_bgr is None or image_bgr.ndim != 3:
            raise ValueError("detect() expects a BGR (H, W, 3) image")

        # Letterbox-resize keeping aspect ratio into the square model input.
        im_h, im_w = image_bgr.shape[:2]
        model_w, model_h = self.input_size
        im_ratio, model_ratio = im_h / im_w, model_h / model_w
        if im_ratio > model_ratio:
            new_h = model_h
            new_w = int(new_h / im_ratio)
        else:
            new_w = model_w
            new_h = int(new_w * im_ratio)
        det_scale = new_h / im_h

        resized = cv2.resize(image_bgr, (new_w, new_h))
        det_img = np.zeros((model_h, model_w, 3), dtype=np.uint8)
        det_img[:new_h, :new_w, :] = resized

        scores_list, bboxes_list, kpss_list = self._forward(det_img, self.det_threshold)
        scores = np.vstack(scores_list) if scores_list else np.empty((0, 1))
        if scores.shape[0] == 0:
            return []

        scores_ravel = scores.ravel()
        order = scores_ravel.argsort()[::-1]
        bboxes = np.vstack(bboxes_list) / det_scale
        pre_det = np.hstack((bboxes, scores)).astype(np.float32)[order]
        keep = _nms(pre_det, self.nms_threshold)
        det = pre_det[keep]

        if self.use_kps:
            kpss = (np.vstack(kpss_list) / det_scale)[order][keep]
        else:
            kpss = np.zeros((det.shape[0], 5, 2), dtype=np.float32)

        if max_num > 0 and det.shape[0] > max_num:
            det, kpss = self._keep_top(det, kpss, image_bgr.shape, max_num)

        return [
            DetectedFace(
                bbox=det[i, :4].copy(),
                score=float(det[i, 4]),
                landmarks=kpss[i].copy(),
            )
            for i in range(det.shape[0])
        ]

    @staticmethod
    def _keep_top(
        det: np.ndarray, kpss: np.ndarray, img_shape: tuple, max_num: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Keep the `max_num` largest faces weighted toward image center."""
        areas = (det[:, 2] - det[:, 0]) * (det[:, 3] - det[:, 1])
        cx, cy = img_shape[1] / 2, img_shape[0] / 2
        offsets = np.vstack(
            [(det[:, 0] + det[:, 2]) / 2 - cx, (det[:, 1] + det[:, 3]) / 2 - cy]
        )
        dist_sq = np.sum(offsets**2, axis=0)
        scores = areas - dist_sq * 2.0
        idx = np.argsort(scores)[::-1][:max_num]
        return det[idx], kpss[idx]
