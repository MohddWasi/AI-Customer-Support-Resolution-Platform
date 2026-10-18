import enum
import uuid

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RetrievalMethod(str, enum.Enum):
    VECTOR = "vector"
    LEXICAL = "lexical"  # BM25 / full-text search
    HYBRID_RRF = "hybrid_rrf"  # vector + lexical merged with Reciprocal Rank Fusion
    RERANKED = "reranked"


class RetrievalResult(Base, TimestampMixin):
    """A chunk returned by retrieval during an AI run, with its rank and score."""

    __tablename__ = "retrieval_results"

    __table_args__ = (
        CheckConstraint("rank >= 1", name="rank_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Step that performed the retrieval
    ai_run_step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ai_run_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Empty if the chunk was later deleted (e.g. re-ingestion); the result stays for evaluation
    document_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Query actually sent to retrieval (after rewriting, if any)
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    retrieval_method: Mapped[RetrievalMethod] = mapped_column(
        Enum(
            RetrievalMethod,
            name="retrieval_method",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )

    # Position in the result list, starting at 1
    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Method-specific score (cosine similarity, BM25, RRF or reranker score)
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
