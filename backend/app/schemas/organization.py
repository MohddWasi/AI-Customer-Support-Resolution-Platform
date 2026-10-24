import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.organization_member import OrganizationRole
from app.schemas.auth import normalize_email


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


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: OrganizationRole

    _normalize_email = field_validator("email")(normalize_email)


class UpdateMemberRoleRequest(BaseModel):
    role: OrganizationRole
