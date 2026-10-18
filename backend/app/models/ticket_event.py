import enum
import uuid
from typing import Any

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TicketEventType(str, enum.Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ASSIGNED = "assigned"
    CLASSIFIED = "classified"


class EventActorType(str, enum.Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    AI = "ai"
    SYSTEM = "system"


class TicketEvent(Base, TimestampMixin):
    """Lifecycle history of a ticket (status changes, assignment, classification)."""

    __tablename__ = "ticket_events"

    __table_args__ = (
        # Ticket history is read as "all events of a ticket, oldest first"
        Index("ix_ticket_events_ticket_id_created_at", "ticket_id", "created_at"),
        # AI and system events never belong to a user
        CheckConstraint(
            "actor_type NOT IN ('ai', 'system') OR actor_user_id IS NULL",
            name="non_user_actor_has_no_user",
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

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        # no separate index: ix_ticket_events_ticket_id_created_at starts with this column
    )

    event_type: Mapped[TicketEventType] = mapped_column(
        Enum(
            TicketEventType,
            name="ticket_event_type",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )

    actor_type: Mapped[EventActorType] = mapped_column(
        Enum(
            EventActorType,
            name="event_actor_type",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Event-specific data, e.g. {"from": "new", "to": "in_progress"} for status changes
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
