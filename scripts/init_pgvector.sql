-- Executed once on first DB init (mounted into postgres entrypoint).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
