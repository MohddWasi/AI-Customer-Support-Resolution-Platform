import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Citation(Base, TimestampMixin):
    """Evidence backing a claim in an AI response, traceable to a source chunk."""

    __tablename__ = "citations"

    __table_args__ = (
        CheckConstraint("citation_number >= 1", name="citation_number_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The AI message this citation supports; empty while the response is still a draft
    ticket_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ticket_messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Source links are kept nullable so citations survive re-ingestion of the source
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Number shown in the response, e.g. [1]
    citation_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Snapshot of the source, shown to the agent even if the document changes later
    source_title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    # The exact text from the chunk that supports the claim
    text_span: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    retrieval_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
