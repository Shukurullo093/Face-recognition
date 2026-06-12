"""Face repository — owns the pgvector ANN search (hot path)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face import Face
from app.models.person import Person
from app.repositories.base import BaseRepository


@dataclass(slots=True)
class SearchRow:
    face_id: uuid.UUID
    person_id: uuid.UUID
    full_name: str
    similarity: float


class FaceRepository(BaseRepository[Face]):
    model = Face

    def __init__(self, session: AsyncSession, ef_search: int = 80) -> None:
        super().__init__(session)
        self.ef_search = ef_search

    async def list_by_person(self, person_id: uuid.UUID) -> list[Face]:
        stmt = select(Face).where(Face.person_id == person_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_with_person(
        self, limit: int = 24, offset: int = 0, person_id: uuid.UUID | None = None
    ) -> list[tuple[Face, str]]:
        """Faces joined to their person's name, newest first (gallery view).

        Optionally filtered to a single person (used by Verify to show the
        claimed identity's enrolled image).
        """
        stmt = (
            select(Face, Person.full_name)
            .join(Person, Person.id == Face.person_id)
            .order_by(Face.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if person_id is not None:
            stmt = stmt.where(Face.person_id == person_id)
        rows = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in rows.all()]

    async def search(
        self, embedding: list[float], top_k: int, only_active: bool = True
    ) -> list[SearchRow]:
        """1:N identification via pgvector cosine distance (`<=>`).

        Cosine distance d in [0, 2]; cosine similarity = 1 - d. The HNSW index
        on faces.embedding makes this sub-linear; `hnsw.ef_search` trades recall
        for latency at query time.
        """
        # Tune recall/latency for this session's index scans.
        # SET does not accept bind params in PostgreSQL; inline the validated int.
        await self.session.execute(text(f"SET LOCAL hnsw.ef_search = {int(self.ef_search)}"))

        # Filter on faces.is_active (a trigger-synced mirror of persons.is_active)
        # so the planner can use the PARTIAL HNSW index `ix_faces_embedding_hnsw_active`
        # — the active filter becomes a pre-filter on the index instead of a
        # post-filter that drops recall after the ANN scan returns its candidates.
        active_clause = "AND f.is_active" if only_active else ""
        stmt = text(
            f"""
            SELECT f.id            AS face_id,
                   f.person_id     AS person_id,
                   p.full_name     AS full_name,
                   1 - (f.embedding <=> :query_vec) AS similarity
            FROM faces f
            JOIN persons p ON p.id = f.person_id
            WHERE TRUE {active_clause}
            ORDER BY f.embedding <=> :query_vec
            LIMIT :top_k
            """
        )
        # pgvector accepts the bracketed string form for a vector literal.
        query_vec = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
        result = await self.session.execute(stmt, {"query_vec": query_vec, "top_k": top_k})
        return [
            SearchRow(
                face_id=row.face_id,
                person_id=row.person_id,
                full_name=row.full_name,
                similarity=float(row.similarity),
            )
            for row in result
        ]

    async def best_match_for_person(
        self, person_id: uuid.UUID, embedding: list[float]
    ) -> tuple[uuid.UUID, float] | None:
        """1:1 — closest enrolled face of one person; returns (face_id, similarity)."""
        # SET does not accept bind params in PostgreSQL; inline the validated int.
        await self.session.execute(text(f"SET LOCAL hnsw.ef_search = {int(self.ef_search)}"))
        stmt = text(
            """
            SELECT f.id AS face_id,
                   1 - (f.embedding <=> :query_vec) AS similarity
            FROM faces f
            WHERE f.person_id = :person_id
            ORDER BY f.embedding <=> :query_vec
            LIMIT 1
            """
        )
        query_vec = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
        row = (
            await self.session.execute(
                stmt, {"query_vec": query_vec, "person_id": str(person_id)}
            )
        ).first()
        if row is None:
            return None
        return row.face_id, float(row.similarity)

    async def count(self, person_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count()).select_from(Face)
        if person_id is not None:
            stmt = stmt.where(Face.person_id == person_id)
        return await self.session.scalar(stmt) or 0
