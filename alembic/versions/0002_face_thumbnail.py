"""add faces.thumbnail (small JPEG crop for the gallery)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Small (~max 220px) JPEG crop of the enrolled face, stored inline so the
    # dashboard gallery can render thumbnails without a separate object store.
    op.add_column("faces", sa.Column("thumbnail", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("faces", "thumbnail")
