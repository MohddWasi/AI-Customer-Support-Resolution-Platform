from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
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
