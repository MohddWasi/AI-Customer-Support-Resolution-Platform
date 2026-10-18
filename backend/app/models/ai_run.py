import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AiRunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"  # retries exhausted, moved to the dead-letter queue
    CANCELLED = "cancelled"


class AiRun(Base, TimestampMixin):
    """One AI resolution attempt for a ticket. Also tracks the background job's state."""

    __tablename__ = "ai_runs"

    __table_args__ = (
        # The same request must never start two runs (job retries reuse the key)
        UniqueConstraint("organization_id", "idempotency_key", name="uq_ai_runs_organization_idempotency_key"),
        # Run history of a ticket, newest or oldest first
        Index("ix_ai_runs_ticket_id_created_at", "ticket_id", "created_at"),
        # Monitoring: runs of an organization by status (e.g. failed, waiting_for_human)
        Index("ix_ai_runs_organization_id_status", "organization_id", "status"),
        CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
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
        # no separate index: the unique constraint and ix_ai_runs_organization_id_status start with it
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        # no separate index: ix_ai_runs_ticket_id_created_at starts with this column
    )

    # User who requested the run; empty for automatic runs
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[AiRunStatus] = mapped_column(
        Enum(
            AiRunStatus,
            name="ai_run_status",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=AiRunStatus.QUEUED,
        server_default=AiRunStatus.QUEUED.value,
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Failure reason when status is failed or dead_lettered
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    final_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Langfuse trace for this run
    trace_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    total_input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
