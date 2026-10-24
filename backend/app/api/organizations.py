from fastapi import APIRouter, Depends
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.schemas.organization import OrganizationResponse

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=list[OrganizationResponse])
async def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """Organizations the current user belongs to, with their role in each."""
    rows = await db.execute(
        Select(Organization.id, Organization.name, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(Organization.name)
    )
    return [OrganizationResponse(id=org_id, name=name, role=role) for org_id, name, role in rows]
