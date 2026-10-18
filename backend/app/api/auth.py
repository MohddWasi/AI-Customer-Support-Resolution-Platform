import http

from fastapi import Depends, HTTPException, status, APIRouter
from httpx import get
from sqlalchemy import Select
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.user import User
from app.schemas.auth import RegisterRequest, UserResponse

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

        org = Organization(
            name = data.organization_name
        )

        db.add_all([user,org])
        await db.flush()

        membership  = OrganizationMember(
            user_id = user.id,
            organization_id = org.id,
            organization_role = OrganizationRole.admin
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration."
        ) from e

    