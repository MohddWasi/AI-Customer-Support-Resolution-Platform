import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DocumentSourceType(str, enum.Enum):
    """Kind of knowledge a document holds. Kept separate so retrieval can filter by it."""

    PRODUCT_DOCS = "product_docs"
    TROUBLESHOOTING = "troubleshooting"
    INTERNAL_POLICY = "internal_policy"
    HISTORICAL_TICKET = "historical_ticket"
    FAQ = "faq"
    RELEASE_NOTE = "release_note"


class DocumentAccessLevel(str, enum.Enum):
    """Who may retrieve a document: customers (public) or support staff only (internal)."""

    PUBLIC = "public"
    INTERNAL = "internal"


class Document(Base, TimestampMixin):
    """A single ingested document (web page, policy, FAQ, historical ticket, ...)."""

    __tablename__ = "documents"

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

    knowledge_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
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

    # Defaults to internal so a document is never exposed to customers by accident
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

    # SHA-256 of the cleaned content, used to skip unchanged documents on re-ingestion
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
