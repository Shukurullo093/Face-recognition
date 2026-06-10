"""initial schema: pgvector, users, persons, faces, recognition_logs + HNSW index

Revision ID: 0001
Revises:
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 512


def upgrade() -> None:
    # Extensions (idempotent; also created by init script in docker).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # gen_random_uuid()

    # create_type=False so the explicit .create() below is the single source of
    # the CREATE TYPE; otherwise create_table() would emit a duplicate CREATE TYPE.
    user_role = postgresql.ENUM(
        "admin", "operator", "viewer", name="user_role", create_type=False
    )
    rec_action = postgresql.ENUM(
        "register", "verify", "search", "import", name="recognition_action", create_type=False
    )
    user_role.create(op.get_bind(), checkfirst=True)
    rec_action.create(op.get_bind(), checkfirst=True)

    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ---- persons ----
    op.create_table(
        "persons",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_persons_external_id", "persons", ["external_id"], unique=True)

    # ---- faces ----
    op.create_table(
        "faces",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("det_score", sa.Float(), nullable=False),
        sa.Column("quality", sa.Float(), nullable=True),
        sa.Column("image_path", sa.String(1024), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_faces_person_id", "faces", ["person_id"])

    # HNSW index for cosine distance (<=>). Tuned for accuracy/build-time balance.
    # m = graph degree, ef_construction = build-time candidate list size.
    op.execute(
        "CREATE INDEX ix_faces_embedding_hnsw ON faces "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 200)"
    )

    # ---- recognition_logs ----
    op.create_table(
        "recognition_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("action", rec_action, nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("matched_face_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("client_ip", sa.String(64), nullable=True),
        sa.Column("message", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recognition_logs_action", "recognition_logs", ["action"])
    op.create_index("ix_recognition_logs_user_id", "recognition_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("recognition_logs")
    op.execute("DROP INDEX IF EXISTS ix_faces_embedding_hnsw")
    op.drop_table("faces")
    op.drop_table("persons")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS recognition_action")
    op.execute("DROP TYPE IF EXISTS user_role")
