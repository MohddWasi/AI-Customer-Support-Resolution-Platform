import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.user import User
from app.schemas.organization import AddMemberRequest, MemberResponse, OrganizationResponse, UpdateMemberRoleRequest

router = APIRouter(prefix="/organizations", tags=["Organizations"])


async def get_membership_or_404(db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID) -> OrganizationMember:
    membership = await db.scalar(
        Select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
    return membership


async def ensure_another_admin_remains(db: AsyncSession, membership: OrganizationMember) -> None:
    """Refuse to demote or remove the organization's last admin."""
    if membership.role != OrganizationRole.ADMIN:
        return
    # Lock the admin rows so two concurrent requests can't both remove "the other" admin
    admin_ids = (await db.scalars(
        Select(OrganizationMember.id)
        .where(
            OrganizationMember.organization_id == membership.organization_id,
            OrganizationMember.role == OrganizationRole.ADMIN,
        )
        .with_for_update()
    )).all()
    if len(admin_ids) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization must keep at least one admin.",
        )


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


@router.get("/{organization_id}/members", response_model=list[MemberResponse])
async def list_members(
    organization_id: uuid.UUID,
    _: OrganizationMember = Depends(require_roles(OrganizationRole.ADMIN, OrganizationRole.SUPPORT_AGENT)),
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    """Members of an organization (admins and support agents only)."""
    rows = await db.execute(
        Select(User.id, User.email, User.full_name, OrganizationMember.role, OrganizationMember.created_at)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(User.full_name)
    )
    return [
        MemberResponse(user_id=user_id, email=email, full_name=full_name, role=role, joined_at=joined_at)
        for user_id, email, full_name, role, joined_at in rows
    ]


@router.post("/{organization_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    organization_id: uuid.UUID,
    data: AddMemberRequest,
    _: OrganizationMember = Depends(require_roles(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """Add an existing account to the organization with a role (admins only)."""
    user = await db.scalar(Select(User).where(User.email == data.email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account with this email. The user must register first.",
        )

    membership = OrganizationMember(organization_id=organization_id, user_id=user.id, role=data.role)
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization.",
        ) from e

    return MemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        joined_at=membership.created_at,
    )


@router.patch("/{organization_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    _: OrganizationMember = Depends(require_roles(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """Change a member's role (admins only)."""
    membership = await get_membership_or_404(db, organization_id, user_id)
    if data.role != membership.role:
        if data.role != OrganizationRole.ADMIN:
            await ensure_another_admin_remains(db, membership)
        membership.role = data.role
        await db.commit()

    user = await db.get(User, user_id)
    return MemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        joined_at=membership.created_at,
    )
