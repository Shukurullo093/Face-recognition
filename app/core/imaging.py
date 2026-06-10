"""Small image helpers (thumbnail generation for the gallery)."""
from __future__ import annotations

import numpy as np
import cv2


def make_face_thumbnail(
    image_bgr: np.ndarray,
    bbox: np.ndarray,
    *,
    max_size: int = 220,
    margin: float = 0.3,
    jpeg_quality: int = 85,
) -> bytes | None:
    """Crop the face region (with margin) and encode a JPEG thumbnail.

    Args:
        image_bgr: source BGR image the face was detected in.
        bbox: (4,) array [x1, y1, x2, y2] in image-pixel coordinates.
        max_size: longest side of the resulting thumbnail in pixels.
        margin: fraction of the box size added as padding around the face.

    Returns:
        JPEG bytes, or None if the crop is empty / encoding fails.
    """
    h, w = image_bgr.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in bbox)
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    X1 = max(0, int(x1 - mx))
    Y1 = max(0, int(y1 - my))
    X2 = min(w, int(x2 + mx))
    Y2 = min(h, int(y2 + my))
    if X2 <= X1 or Y2 <= Y1:
        return None

    crop = image_bgr[Y1:Y2, X1:X2]
    if crop.size == 0:
        return None

    ch, cw = crop.shape[:2]
    scale = max_size / max(ch, cw)
    if scale < 1.0:
        crop = cv2.resize(crop, (max(1, int(cw * scale)), max(1, int(ch * scale))))

    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    return buf.tobytes() if ok else None
