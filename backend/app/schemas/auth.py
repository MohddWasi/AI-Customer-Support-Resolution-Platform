import uuid

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


def normalize_email(value: str) -> str:
    """Emails are case-insensitive: store and compare them lowercased."""
    return value.strip().lower()


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    # Omit to create just an account, which an organization admin can then add as a member
    organization_name: str | None = Field(default=None, min_length=2, max_length=150)

    _normalize_email = field_validator("email")(normalize_email)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    # max_length: hashing a huge password is slow, so cap it like registration does
    password: str = Field(max_length=128)

    _normalize_email = field_validator("email")(normalize_email)