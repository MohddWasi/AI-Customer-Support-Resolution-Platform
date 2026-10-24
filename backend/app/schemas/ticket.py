import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketPriority, TicketStatus


class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    # The customer's description of the issue; stored as the ticket's first message
    message: str = Field(min_length=1, max_length=10000)
    priority: TicketPriority = TicketPriority.MEDIUM
    # Only for support agents/admins logging a ticket on behalf of a customer
    customer_id: uuid.UUID | None = None


class TicketResponse(BaseModel):
    id: uuid.UUID
    number: int
    subject: str
    status: TicketStatus
    priority: TicketPriority
    customer_id: uuid.UUID
    assigned_to_user_id: uuid.UUID | None
    category: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TicketAssignRequest(BaseModel):
    # null unassigns the ticket (back to the queue)
    assignee_user_id: uuid.UUID | None
