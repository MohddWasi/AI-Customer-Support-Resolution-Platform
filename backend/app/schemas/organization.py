import uuid

from pydantic import BaseModel

from app.models.organization_member import OrganizationRole


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: OrganizationRole
