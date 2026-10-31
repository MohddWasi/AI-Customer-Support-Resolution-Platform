from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
import jwt
import pytest
from uuid import uuid4

def test_password_hash_and_verification():
    password = "myTestPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_access_token_cntains_user_id():
    user_id = uuid4()

    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload['sub'] == str(user_id)
    assert 'iat' in payload
    assert 'exp' in payload

def test_expired_token_is_rejected():
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": 1},
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )
    
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)

def test_unrecognized_hash_never_matches():
    # e.g. seeded users, whose placeholder is not a real hash
    assert verify_password("anything", "!seed-user-no-login") is False
