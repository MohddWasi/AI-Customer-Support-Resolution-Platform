import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class HumanReviewType(str, enum.Enum):
    RESPONSE = "response"  # an AI-proposed reply to the customer
    TOOL_ACTION = "tool_action"  # a sensitive tool call waiting for approval


class HumanReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"  # approved after the reviewer changed the response
    REJECTED = "rejected"
    ESCALATED = "escalated"


class HumanReview(Base, TimestampMixin):
    """A support agent's review of an AI-proposed response or sensitive action."""

    __tablename__ = "human_reviews"

    __table_args__ = (
        # Review queue: pending reviews of an organization
        Index("ix_human_reviews_organization_id_status", "organization_id", "status"),
        # A decision time exists exactly when the review is no longer pending
        CheckConstraint(
            "(status = 'pending') = (decided_at IS NULL)",
            name="decided_at_matches_status",
        ),
        CheckConstraint(
            "review_type <> 'tool_action' OR tool_call_id IS NOT NULL",
            name="tool_action_has_tool_call",
        ),
        CheckConstraint(
            "status <> 'edited' OR edited_response IS NOT NULL",
            name="edited_has_response",
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
        # no separate index: ix_human_reviews_organization_id_status starts with this column
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # The proposed action, for tool_action reviews
    tool_call_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tool_calls.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    review_type: Mapped[HumanReviewType] = mapped_column(
        Enum(
            HumanReviewType,
            name="human_review_type",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )

    status: Mapped[HumanReviewStatus] = mapped_column(
        Enum(
            HumanReviewStatus,
            name="human_review_status",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=HumanReviewStatus.PENDING,
        server_default=HumanReviewStatus.PENDING.value,
        nullable=False,
    )

    # Why review is needed, e.g. "refund requested" or "answer not supported by evidence"
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Agent who made the decision
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewer_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    edited_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
