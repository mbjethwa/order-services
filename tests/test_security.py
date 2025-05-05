from http.client import HTTPException
import pytest
from datetime import timedelta, datetime, timezone
from jose import jwt
from app.core.security import validate_token
from app.core.config import settings



def test_validate_token_valid():
    # Arrange
    username = "testuser"
    user_id = 1
    roles = ["admin"]
    permissions = ["read", "write"]
    expires_delta = timedelta(minutes=15)
    encode = {
        "username": username,
        "user_id": user_id,
        "roles": roles,
        "permissions": permissions,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    # Generate a token using the secret key and algorithm
    token = jwt.encode(encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    credentials = type("HTTPAuthorizationCredentials", (object,), {"credentials": token})

    # Act
    payload = validate_token(credentials)

    # Assert
    assert payload["username"] == username
    assert payload["user_id"] == user_id
    assert payload["roles"] == roles
    assert payload["permissions"] == permissions


