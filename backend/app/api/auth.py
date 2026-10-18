import http
import logging
from fastapi import Depends, HTTPException, status, APIRouter
from sqlalchemy import Select
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.user import User
from app.schemas.auth import RegisterRequest, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register",response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data:RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:

    existing_user = await db.scalar(
        Select(User).where(User.email == data.email)
        );
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered."
        )

    try:
        user = User(
            email = data.email,
            full_name = data.full_name,
            hashed_password = data.password
        )

        existing_org = await db.scalar(
            Select(Organization).where(
                Organization.name == data.organization_name
                )
        )
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Organization already exists. Ask an administrator for an invitation."
            )
        org = Organization(
            name = data.organization_name
        )

        db.add_all([user,org])
        await db.flush()

        membership  = OrganizationMember(
            user_id = user.id,
            organization_id = org.id,
            role = OrganizationRole.CUSTOMER
        )

        db.add(membership)
        await db.commit()
        await db.refresh(user)

        return UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name
        )
    
    except Exception as e:
        await db.rollback()
        logger.exception("Error during registration: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration."
        ) from e

    