"""Background workers. Bulk import currently runs via FastAPI BackgroundTasks
(see app.services.bulk_import_service); this package is the seam to move that
onto a dedicated queue (Celery/arq) without touching the API layer."""
