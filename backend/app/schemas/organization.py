import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.organization_member import OrganizationRole


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: OrganizationRole


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: OrganizationRole
    joined_at: datetime
