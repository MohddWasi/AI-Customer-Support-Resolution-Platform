import hashlib
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import (
    AiRun,
    AiRunStep,
    AuditLog,
    Citation,
    Document,
    DocumentChunk,
    EvaluationRun,
    HumanReview,
    KnowledgeSource,
    Organization,
    OrganizationMember,
    RetrievalResult,
    Ticket,
    TicketEvent,
    TicketMessage,
    ToolCall,
    User,
)
from app.models.audit_log import AuditActorType, AuditOutcome
from app.models.document import DocumentAccessLevel, DocumentSourceType
from app.models.document_chunk import EMBEDDING_DIMENSIONS
from app.models.human_review import HumanReviewType
from app.models.organization_member import OrganizationRole
from app.models.retrieval_result import RetrievalMethod
from app.models.ticket_event import EventActorType, TicketEventType
from app.models.ticket_message import MessageSenderType


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session inside a transaction that is always rolled back, so tests leave no data behind."""
    # NullPool: each test gets a fresh connection on its own event loop
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


def unit_vector(index: int) -> list[float]:
    """An embedding pointing along one axis; vectors with different indexes are dissimilar."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[index] = 1.0
    return vector


@dataclass
class Tenant:
    """One organization with one row in every tenant-owned table."""

    organization: Organization
    ids: dict[str, uuid.UUID] = field(default_factory=dict)  # table name -> id of its row


async def make_tenant(session: AsyncSession, name: str, embedding: list[float]) -> Tenant:
    suffix = uuid.uuid4().hex[:8]
    org = Organization(name=f"{name} {suffix}")
    customer = User(email=f"customer-{suffix}@{name.lower()}.test", full_name="Customer", hashed_password="!")
    agent = User(email=f"agent-{suffix}@{name.lower()}.test", full_name="Agent", hashed_password="!")
    session.add_all([org, customer, agent])
    await session.flush()

    def add(model: type, **values: Any) -> Any:
        row = model(organization_id=org.id, **values)
        session.add(row)
        return row

    member = add(OrganizationMember, user_id=customer.id, role=OrganizationRole.CUSTOMER)
    add(OrganizationMember, user_id=agent.id, role=OrganizationRole.SUPPORT_AGENT)
    ticket = add(Ticket, customer_id=customer.id, subject=f"{name} ticket")
    source = add(KnowledgeSource, name=f"{name} docs")
    await session.flush()

    message = add(TicketMessage, ticket_id=ticket.id, sender_type=MessageSenderType.CUSTOMER,
                  sender_user_id=customer.id, content=f"{name} message")
    event = add(TicketEvent, ticket_id=ticket.id, event_type=TicketEventType.CREATED,
                actor_type=EventActorType.CUSTOMER, actor_user_id=customer.id)
    document = add(Document, knowledge_source_id=source.id, title=f"{name} document",
                   source_type=DocumentSourceType.PRODUCT_DOCS, access_level=DocumentAccessLevel.PUBLIC,
                   content_hash=hashlib.sha256(name.encode()).hexdigest())
    run = add(AiRun, ticket_id=ticket.id, idempotency_key=f"run-{suffix}")
    await session.flush()

    chunk = add(DocumentChunk, document_id=document.id, chunk_index=0, content=f"{name} chunk",
                embedding=embedding, source_type=document.source_type, access_level=document.access_level)
    step = add(AiRunStep, ai_run_id=run.id, step_index=0, agent="knowledge_research", name="hybrid_search")
    await session.flush()

    retrieval = add(RetrievalResult, ai_run_id=run.id, ai_run_step_id=step.id, document_chunk_id=chunk.id,
                    query=f"{name} query", retrieval_method=RetrievalMethod.VECTOR, rank=1, score=0.9)
    tool_call = add(ToolCall, ticket_id=ticket.id, ai_run_id=run.id, tool_name="get_customer_account")
    citation = add(Citation, ticket_id=ticket.id, ai_run_id=run.id, document_id=document.id,
                   document_chunk_id=chunk.id, citation_number=1, text_span=f"{name} evidence")
    review = add(HumanReview, ticket_id=ticket.id, ai_run_id=run.id, review_type=HumanReviewType.RESPONSE,
                 reason="low confidence")
    evaluation = add(EvaluationRun, name=f"{name} eval", experiment="vector", dataset_name="smoke")
    audit = add(AuditLog, actor_type=AuditActorType.USER, actor_user_id=agent.id, action="ticket.viewed",
                ticket_id=ticket.id, outcome=AuditOutcome.SUCCESS)
    await session.flush()

    rows = [member, ticket, source, message, event, document, run, chunk, step, retrieval,
            tool_call, citation, review, evaluation, audit]
    return Tenant(organization=org, ids={type(row).__tablename__: row.id for row in rows})
