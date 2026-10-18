import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AiRunStepStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AiRunStep(Base, TimestampMixin):
    """One step of an AI run, performed by one agent (created_at is when it started)."""

    __tablename__ = "ai_run_steps"

    __table_args__ = (
        UniqueConstraint("ai_run_id", "step_index", name="uq_ai_run_steps_run_step_index"),
        CheckConstraint("step_index >= 0", name="step_index_non_negative"),
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

    ai_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=False,
        # no separate index: uq_ai_run_steps_run_step_index starts with this column
    )

    # Order of the step within its run, starting at 0
    step_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Agent that ran the step, e.g. "supervisor", "knowledge_research", "verification"
    agent: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # What the step did, e.g. "classify_ticket", "hybrid_search", "verify_citations"
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[AiRunStepStatus] = mapped_column(
        Enum(
            AiRunStepStatus,
            name="ai_run_step_status",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=AiRunStepStatus.RUNNING,
        server_default=AiRunStepStatus.RUNNING.value,
        nullable=False,
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    input: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    output: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
