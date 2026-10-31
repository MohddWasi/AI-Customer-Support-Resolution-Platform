from datetime import datetime, timedelta, timezone
from app.core.config import settings
from uuid import UUID
import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(password, hashed_password)
    except UnknownHashError:
        # Not a real hash (e.g. seeded users without a usable password): never matches
        return False

def create_access_token(user_id : UUID) -> str:
    now = datetime.now(tz=timezone.utc)
    payload= {
        'sub': str(user_id),
        'iat': now,
        'exp': now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])


