import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MessageSenderType(str, enum.Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    AI = "ai"


class TicketMessage(Base, TimestampMixin):
    """A message within a support ticket conversation."""

    __tablename__ = "ticket_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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