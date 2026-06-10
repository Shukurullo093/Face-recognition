# Face Recognition System

Production-grade face recognition backend: **SCRFD-2.5GF** detection +
**ArcFace-r100** 512-D embeddings + **PostgreSQL/pgvector** ANN search, served
by an async **FastAPI** API with JWT/RBAC, rate limiting and audit logging.

```
Image ─▶ SCRFD detect ─▶ 5-pt align (112×112) ─▶ ArcFace ─▶ 512-D L2-norm
      ─▶ pgvector (HNSW, cosine) ─▶ register / verify (1:1) / search (1:N)
```

## Architecture

Clean / layered architecture with Repository Pattern and Dependency Injection:

```
app/
├── api/            HTTP layer (routers, deps = composition root)
│   └── v1/         auth, persons, faces, health
├── core/           config, security (JWT/RBAC), logging, exceptions, rate-limit
├── db/             async engine, session, declarative base
├── models/         SQLAlchemy ORM (persons, faces, users, recognition_logs)
├── schemas/        Pydantic v2 request/response models
├── repositories/   data access (incl. pgvector ANN queries)
├── services/       business logic (recognition, auth, bulk-import)
├── recognition/    ML infrastructure
│   ├── detector/   SCRFD (ONNX Runtime CUDA)
│   ├── aligner/    similarity-transform 5-pt alignment
│   ├── arcface/    embedding extractor
│   └── search/     cosine-similarity helpers
├── workers/        background-task seam
└── tests/          unit tests (no GPU/DB required)
```

**Dependency rule:** `api → services → repositories → models/db`. Services depend
on the `BaseDetector` abstraction, not SCRFD — swap detectors without touching
business code (DIP). The ML pipeline is a startup singleton on `app.state`;
blocking ONNX inference is offloaded with `asyncio.to_thread` to keep the event
loop free.

## API

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/token` | — | OAuth2 password login → JWT |
| POST | `/api/v1/auth/users` | admin | Create user |
| POST | `/api/v1/persons` | operator | Create person |
| GET  | `/api/v1/persons` | viewer | List persons |
| POST | `/api/v1/faces/register` | operator | Enroll a face |
| POST | `/api/v1/faces/verify` | viewer | 1:1 verification |
| POST | `/api/v1/faces/search` | viewer | 1:N identification |
| POST | `/api/v1/faces/import` | admin | Start bulk folder import |
| GET  | `/api/v1/faces/import/{job_id}` | admin | Import progress |
| GET  | `/api/v1/stats` | viewer | Aggregate counts + match rate (dashboard) |
| GET  | `/api/v1/logs` | viewer | Recent recognition events (dashboard) |
| GET  | `/api/v1/health`, `/ready` | — | Probes |

Interactive docs at `/docs`.

## Dashboard

A zero-build static web console — **SENTINEL** — ships in `frontend/` and is
auto-mounted by FastAPI at **`/dashboard`** (e.g. http://localhost:8000/dashboard/).
It is a forensic biometric command console: dark terminal aesthetic, a HUD
"viewfinder" that draws a targeting reticle over the detected face, an animated
similarity meter, and live audit telemetry.

Views: **Overview** (stats + activity), **Enroll**, **Verify 1:1**,
**Identify 1:N**, **Persons**, **Face Gallery** (thumbnails + 512-D embedding
fingerprints), **Bulk Import** (live progress), **Audit Log**.

The **Face Gallery** (`GET /faces`) shows each enrolled face as a card with its
thumbnail and a heatmap "fingerprint" of the embedding; clicking a card opens
the full 512-D fingerprint and metadata. A small JPEG crop is stored per face
(`faces.thumbnail`, populated on enroll/import) — faces enrolled before this
column existed show a placeholder.
Navigation is gated by the JWT role (viewer / operator / admin). Log in with an
operator account; the API endpoint field defaults to the page origin and can be
pointed at a remote backend. No Node toolchain required — plain HTML/CSS/JS
served as static files.

**Image input** — every capture surface (Enroll / Verify / Identify) accepts a
file via drag-and-drop or browse, **or a live webcam capture**: click the camera
icon to start the feed, then the shutter to grab a frame (`getUserMedia` →
canvas → JPEG). The stream is released automatically on capture or when you
leave the view. Note: browsers only expose the camera on a **secure context** —
`http://localhost` or HTTPS; a plain `http://<LAN-ip>` origin will block it.

## Quick start (Docker + GPU)

```bash
cp .env.example .env                # then set JWT_SECRET_KEY (openssl rand -hex 32)
# Put ONNX models in ./models  (see scripts/download_models.md)
docker compose up --build           # runs alembic + uvicorn; postgres has pgvector

# Bootstrap an admin (or set BOOTSTRAP_ADMIN_USER/PASSWORD env before up)
docker compose exec api python -m scripts.create_admin admin 'StrongPass123'

# dockersiz ishlatish
sudo apt install postgresql-16-pgvector      # parol so'raydi — shuning uchun men qila olmadim
sudo systemctl restart postgresql

# .env da portni qaytaring:  POSTGRES_PORT=5432
docker rm -f fr-pgvector                      # konteynerni o'chirish
alembic upgrade head                          # lokal PG'da schema + HNSW yaratadi
python -m scripts.create_admin admin 'StrongPass123'
```

Requires the **NVIDIA Container Toolkit** for GPU passthrough.

### Example flow

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/token \
  -d 'username=admin&password=StrongPass123' | jq -r .access_token)

PID=$(curl -s -X POST localhost:8000/api/v1/persons -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"full_name":"Jane Doe"}' | jq -r .id)

curl -X POST localhost:8000/api/v1/faces/register -H "Authorization: Bearer $TOKEN" \
  -F "person_id=$PID" -F "image=@jane.jpg"

curl -X POST localhost:8000/api/v1/faces/search -H "Authorization: Bearer $TOKEN" \
  -F "image=@query.jpg"
```

## Performance

Targets on an RTX 4060 with `CUDAExecutionProvider`:

| Stage | Target |
|-------|--------|
| SCRFD detection | < 20 ms |
| ArcFace embedding | < 10 ms |
| pgvector search (100k faces) | < 100 ms |

**Scaling to millions of embeddings**

- HNSW index (`m=16, ef_construction=200`) on `faces.embedding vector_cosine_ops`.
- Query-time recall/latency via `SET LOCAL hnsw.ef_search` (`HNSW_EF_SEARCH`).
- Embeddings are L2-normalised so cosine distance `<=>` == `1 − dot`.
- For >10M rows consider IVFFlat with `lists ≈ √N` plus periodic `ANALYZE`, or
  partition the gallery; the repository interface stays unchanged.

## Tests

Unit tests run without a GPU, models, or database (heavy deps are faked):

```bash
pip install -r requirements.txt        # or a CPU subset
FR_SKIP_MODELS=1 pytest -q
```

## Security

JWT (HS256) auth, three-tier RBAC (admin > operator > viewer), per-IP rate
limiting (slowapi), full audit trail in `recognition_logs`, non-root container,
upload size/type validation.
