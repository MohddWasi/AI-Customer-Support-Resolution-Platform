import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class KnowledgeSource(Base, TimestampMixin):
    """A collection documents are ingested from, e.g. product docs or internal policies."""

    __tablename__ = "knowledge_sources"

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_knowledge_sources_organization_name"),
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
        # no separate index: uq_knowledge_sources_organization_name starts with this column
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Base URL of the source, e.g. the documentation site (empty for locally generated docs)
    url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
