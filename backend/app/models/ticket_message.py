import enum
import uuid

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Index, Text, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MessageSenderType(str, enum.Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    AI = "ai"


class TicketMessage(Base, TimestampMixin):
    """A message within a support ticket conversation."""

    __tablename__ = "ticket_messages"

    __table_args__ = (
        # Conversations are read as "all messages of a ticket, oldest first"
        Index("ix_ticket_messages_ticket_id_created_at", "ticket_id", "created_at"),
        # AI messages never belong to a user. Customer/agent messages may lose their
        # user via SET NULL, so they are not forced to have one.
        CheckConstraint(
            "sender_type <> 'ai' OR sender_user_id IS NULL",
            name="ai_message_has_no_user",
        ),
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
        # no separate index: ix_ticket_messages_ticket_id_created_at starts with this column
    )

    sender_type: Mapped[MessageSenderType] = mapped_column(
        Enum(
            MessageSenderType,
            name="message_sender_type",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )

    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Agent notes and AI drafts that the customer must not see
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
