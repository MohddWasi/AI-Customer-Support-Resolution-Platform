import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_organization_member
from app.db.session import get_db
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_event import EventActorType, TicketEvent, TicketEventType
from app.models.ticket_message import MessageSenderType, TicketMessage
from app.schemas.ticket import TicketCreateRequest, TicketResponse
from app.services.ticket_access import visible_tickets

router = APIRouter(prefix="/organizations/{organization_id}/tickets", tags=["Tickets"])


async def get_visible_ticket_or_404(db: AsyncSession, membership: OrganizationMember, ticket_id: uuid.UUID) -> Ticket:
    # 404 (not 403) for tickets the member can't see, so their existence isn't revealed
    ticket = await db.scalar(visible_tickets(membership).where(Ticket.id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return ticket


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    organization_id: uuid.UUID,
    data: TicketCreateRequest,
    membership: OrganizationMember = Depends(get_organization_member),
    db: AsyncSession = Depends(get_db),
) -> Ticket:
    """Create a ticket. Customers create their own; agents and admins create one on behalf of a customer."""
    is_customer = membership.role == OrganizationRole.CUSTOMER

    if is_customer:
        if data.customer_id not in (None, membership.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers can only create tickets for themselves.",
            )
        customer_id = membership.user_id
    else:
        if data.customer_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="customer_id is required when creating a ticket on behalf of a customer.",
            )
        customer_role = await db.scalar(
            Select(OrganizationMember.role).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == data.customer_id,
            )
        )
        if customer_role != OrganizationRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="customer_id must be a customer of this organization.",
            )
        customer_id = data.customer_id

    ticket = Ticket(
        organization_id=organization_id,
        customer_id=customer_id,
        subject=data.subject,
        priority=data.priority,
    )
    db.add(ticket)
    await db.flush()

    db.add(TicketMessage(
        organization_id=organization_id,
        ticket_id=ticket.id,
        sender_type=MessageSenderType.CUSTOMER if is_customer else MessageSenderType.SUPPORT_AGENT,
        sender_user_id=membership.user_id,
        content=data.message,
    ))
    db.add(TicketEvent(
        organization_id=organization_id,
        ticket_id=ticket.id,
        event_type=TicketEventType.CREATED,
        actor_type=EventActorType.CUSTOMER if is_customer else EventActorType.SUPPORT_AGENT,
        actor_user_id=membership.user_id,
    ))
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    organization_id: uuid.UUID,
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    membership: OrganizationMember = Depends(get_organization_member),
    db: AsyncSession = Depends(get_db),
) -> list[Ticket]:
    """Tickets visible to the current member, newest first."""
    query = visible_tickets(membership)
    if status_filter is not None:
        query = query.where(Ticket.status == status_filter)
    query = query.order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(limit).offset(offset)
    return list((await db.scalars(query)).all())


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    organization_id: uuid.UUID,
    ticket_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_member),
    db: AsyncSession = Depends(get_db),
) -> Ticket:
    """A single ticket, if the current member may see it."""
    return await get_visible_ticket_or_404(db, membership, ticket_id)
