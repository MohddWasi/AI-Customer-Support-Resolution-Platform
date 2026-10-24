from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.user import User

# Reads "Authorization: Bearer <token>"; Swagger shows a token box for it.
# auto_error=False so a missing token gets the same 401 as an invalid one.
bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current user from the access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload.get("sub"))
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise credentials_exception

    user = await db.get(User, user_id)
    # Inactive users are rejected too: a token issued before deactivation must stop working
    if user is None or not user.is_active:
        raise credentials_exception

    return user

async def get_organization_member(
        organization_id : UUID,
        current_user : User = Depends(get_current_user),
        db : AsyncSession = Depends(get_db)
) -> OrganizationMember:
    """Get the current user's membership in the requested organization."""

    membership = await db.scalar(
        Select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if membership is None :
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization."
        )

    return membership
    
def require_roles(*allowed_roles: OrganizationRole):
    """Require the organization member to have one of the specified roles."""

    async def role_checker(
        membership: OrganizationMember = Depends(get_organization_member),
    ) -> OrganizationMember:
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return membership

    return role_checker