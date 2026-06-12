"""denormalize is_active onto faces + partial HNSW index (active-only 1:N search)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-12

Why: 1:N search filtered on `persons.is_active` via a JOIN, applied AFTER the
HNSW index scan (post-filter). When many nearest neighbours belong to inactive
persons they are dropped after the index returns its ef_search candidates, so
the query can return fewer than top_k rows or miss valid active matches.

Fix: mirror is_active onto `faces` (kept in sync by triggers) and build a
PARTIAL HNSW index `WHERE is_active`. Active-only search then scans an index
that already contains only active faces — the filter is a pre-filter, recall is
preserved. Partial-index predicates can only reference the indexed table, which
is why the flag must live on `faces`, not be joined from `persons`.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Denormalized flag on faces, seeded from each face's person.
    op.add_column(
        "faces",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.execute(
        "UPDATE faces f SET is_active = p.is_active "
        "FROM persons p WHERE f.person_id = p.id"
    )

    # 2a. New/reassigned faces inherit their person's current status.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION faces_set_is_active() RETURNS trigger AS $$
        BEGIN
            SELECT p.is_active INTO NEW.is_active
            FROM persons p WHERE p.id = NEW.person_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_faces_set_is_active "
        "BEFORE INSERT OR UPDATE OF person_id ON faces "
        "FOR EACH ROW EXECUTE FUNCTION faces_set_is_active()"
    )

    # 2b. Toggling a person propagates to all their faces.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION persons_propagate_is_active() RETURNS trigger AS $$
        BEGIN
            IF NEW.is_active IS DISTINCT FROM OLD.is_active THEN
                UPDATE faces SET is_active = NEW.is_active WHERE person_id = NEW.id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_persons_propagate_is_active "
        "AFTER UPDATE OF is_active ON persons "
        "FOR EACH ROW EXECUTE FUNCTION persons_propagate_is_active()"
    )

    # 3. Partial HNSW index over active faces only. Raise maintenance_work_mem so
    #    the graph build stays in memory (otherwise it spills to disk — ~8x slower).
    op.execute("SET maintenance_work_mem = '2GB'")
    op.execute(
        "CREATE INDEX ix_faces_embedding_hnsw_active ON faces "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 200) "
        "WHERE is_active"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_faces_embedding_hnsw_active")
    op.execute("DROP TRIGGER IF EXISTS trg_persons_propagate_is_active ON persons")
    op.execute("DROP TRIGGER IF EXISTS trg_faces_set_is_active ON faces")
    op.execute("DROP FUNCTION IF EXISTS persons_propagate_is_active()")
    op.execute("DROP FUNCTION IF EXISTS faces_set_is_active()")
    op.drop_column("faces", "is_active")
