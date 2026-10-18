import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EvaluationRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRun(Base, TimestampMixin):
    """One evaluation experiment over a dataset, e.g. "vector only" vs "hybrid + reranker".

    Metric values stay empty until they are actually measured.
    """

    __tablename__ = "evaluation_runs"

    __table_args__ = (
        # Evaluation dashboard: runs of an organization, newest first
        Index("ix_evaluation_runs_organization_id_created_at", "organization_id", "created_at"),
        CheckConstraint(
            "failed_cases >= 0 AND failed_cases <= total_cases",
            name="failed_cases_within_total",
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
        # no separate index: ix_evaluation_runs_organization_id_created_at starts with this column
    )

    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # e.g. "Experiment C: vector + BM25 + RRF"
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    # Retrieval/agent setup being measured, e.g. "vector", "hybrid_rrf", "reranker", "query_rewriting"
    experiment: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    dataset_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    dataset_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Settings used for the run: retrieval parameters, models, prompt versions
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )

    status: Mapped[EvaluationRunStatus] = mapped_column(
        Enum(
            EvaluationRunStatus,
            name="evaluation_run_status",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=EvaluationRunStatus.RUNNING,
        server_default=EvaluationRunStatus.RUNNING.value,
        nullable=False,
    )

    total_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    failed_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    # Averaged Ragas metrics, e.g. {"context_precision": 0.82, "faithfulness": 0.91, ...}
    metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    avg_latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    p95_latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
