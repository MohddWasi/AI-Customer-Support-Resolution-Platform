import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.document import DocumentAccessLevel, DocumentSourceType

# OpenAI text-embedding-3-small; changing it requires a migration and re-embedding
EMBEDDING_DIMENSIONS = 1536


class DocumentChunk(Base, TimestampMixin):
    """A retrievable piece of a document with its embedding.

    Filter metadata (organization, source type, access level, product, version) is
    copied from the document so retrieval can filter without joining documents.
    """

    __tablename__ = "document_chunks"

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk_index"),
        # Approximate nearest-neighbour search on cosine distance
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
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

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        # no separate index: uq_document_chunks_document_chunk_index starts with this column
    )

    # Position of the chunk within its document, starting at 0
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Heading path of the chunk within the document, e.g. "Two-factor authentication > Recovery codes"
    section: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=False,
    )

    source_type: Mapped[DocumentSourceType] = mapped_column(
        Enum(
            DocumentSourceType,
            name="document_source_type",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )

    access_level: Mapped[DocumentAccessLevel] = mapped_column(
        Enum(
            DocumentAccessLevel,
            name="document_access_level",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=DocumentAccessLevel.INTERNAL,
        server_default=DocumentAccessLevel.INTERNAL.value,
        nullable=False,
    )

    product: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
