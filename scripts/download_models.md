# Obtaining the ONNX models

Place the two ONNX files into `./models/` (mounted read-only into the container
at `/app/models`, matching the `./models/...` paths in `.env`). The default
filenames match `.env.example`.

## SCRFD-2.5GF (detector)
`det_2.5g.onnx` ships in the InsightFace **`buffalo_m`** pack (note: `buffalo_l`
contains `det_10g.onnx`, i.e. SCRFD-10GF — not 2.5g). The download unpacks into a
nested `buffalo_m/buffalo_m/` directory:

```bash
pip install insightface
python3 - <<'PY'
from insightface.utils import storage
storage.ensure_available("models", "buffalo_m", root="~/.insightface")
PY
cp ~/.insightface/models/buffalo_m/buffalo_m/det_2.5g.onnx  ./models/scrfd_2.5g_bnkps.onnx
```

The detector auto-detects whether the export includes keypoints (9 outputs) or
not (6 outputs); `det_2.5g.onnx` includes keypoints.

> Already have `buffalo_l`? `det_10g.onnx` (SCRFD-10GF) is a drop-in — more
> accurate, slightly slower — and works with the same post-processing:
> `cp ~/.insightface/models/buffalo_l/det_10g.onnx ./models/scrfd_2.5g_bnkps.onnx`

## ArcFace (recognition)
The `buffalo_m`/`buffalo_l` packs ship `w600k_r50.onnx` (ResNet-50 @ WebFace600K,
512-D). It is a verified drop-in for the recognition stage:

```bash
cp ~/.insightface/models/buffalo_m/buffalo_m/w600k_r50.onnx ./models/arcface_r100.onnx
```

For a true ResNet-100 backbone use a `glintr100.onnx` export instead. Any
ArcFace export taking a 112×112 face and emitting a 512-D vector is compatible —
the embedder reads the output dimension from the model.

## Verify
```bash
python3 -c "import onnxruntime as ort; \
print(ort.InferenceSession('models/scrfd_2.5g_bnkps.onnx').get_providers())"
```
Expect `CUDAExecutionProvider` present when running on the GPU image.
