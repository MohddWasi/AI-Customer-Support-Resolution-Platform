import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, false, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ToolCallStatus(str, enum.Enum):
    REQUESTED = "requested"
    PENDING_APPROVAL = "pending_approval"  # sensitive action waiting for a human
    APPROVED = "approved"
    REJECTED = "rejected"  # a human rejected the proposed action
    DENIED = "denied"  # the backend blocked it: not authorized for this user/organization/tool
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ToolCall(Base, TimestampMixin):
    """A tool/function the AI called (or proposed to call) during a run."""

    __tablename__ = "tool_calls"

    __table_args__ = (
        # Approval states only make sense for calls that need approval
        CheckConstraint(
            "requires_approval OR status NOT IN ('pending_approval', 'approved', 'rejected')",
            name="approval_status_requires_approval",
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
        index=True,
    )

    ai_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_run_step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ai_run_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # e.g. "get_customer_account", "create_escalation"
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    arguments: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )

    status: Mapped[ToolCallStatus] = mapped_column(
        Enum(
            ToolCallStatus,
            name="tool_call_status",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=ToolCallStatus.REQUESTED,
        server_default=ToolCallStatus.REQUESTED.value,
        nullable=False,
    )

    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # When the tool actually ran (empty if it never ran: rejected, denied or still pending)
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
