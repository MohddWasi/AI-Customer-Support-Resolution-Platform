import enum
import uuid
from typing import Any

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuditActorType(str, enum.Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class AuditOutcome(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"  # blocked by authorization


class AuditLog(Base, TimestampMixin):
    """Record of a sensitive action: who did what, when, on which ticket/tool, with what result.

    All references are SET NULL so the audit trail survives deletion of what it describes.
    """

    __tablename__ = "audit_logs"

    __table_args__ = (
        # Audit trail of an organization, newest first
        Index("ix_audit_logs_organization_id_created_at", "organization_id", "created_at"),
        # AI and system actions never belong to a user
        CheckConstraint(
            "actor_type = 'user' OR actor_user_id IS NULL",
            name="non_user_actor_has_no_user",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Empty for platform-level actions (e.g. registration) or after the organization is deleted
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        # no separate index: ix_audit_logs_organization_id_created_at starts with this column
    )

    actor_type: Mapped[AuditActorType] = mapped_column(
        Enum(
            AuditActorType,
            name="audit_actor_type",
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

    # What happened, e.g. "tool_call.executed", "ticket.closed", "human_review.approved"
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tool_call_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tool_calls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Action details such as tool arguments, with sensitive values redacted before saving
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    outcome: Mapped[AuditOutcome] = mapped_column(
        Enum(
            AuditOutcome,
            name="audit_outcome",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )

    # Request that triggered the action, for correlating with application logs
    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
