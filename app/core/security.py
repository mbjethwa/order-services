from datetime import datetime, timezone
from jose import JWTError, jwt
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from app.core.config import settings
from app.db.base import get_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


db_dependency = Annotated[Session, Depends(get_db)]


security = HTTPBearer()


# This function is used to validate the JWT token and extract the payload.
def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    # Ensure credentials are provided
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    authorization_token = credentials.credentials

    try:
        # Decode the JWT token
        payload = jwt.decode(
            authorization_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Validate the token payload
        username: str = payload.get("username")  # type: ignore
        user_id: int = payload.get("user_id")  # type: ignore

        # Check expiration
        exp_timestamp = payload.get("exp")
        if exp_timestamp is None or datetime.fromtimestamp(exp_timestamp, timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is invalid.",
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired.",
        ) from e


def check_permissions(required_permissions: list[str]):
    """
    Check if the current user has the required permission.

    Args:
        required_permission (list[str]): The list of possible permissions to perform an action.

    Returns:
        function: A permission checker function that raises an HTTPException if the user lacks the required permission.
    """

    def permission_checker(payload: dict = Depends(validate_token)):
        user_permissions = payload.get("permissions", [])

        # Check if user has one of the required permissions
        if not any(
            permission in user_permissions for permission in required_permissions
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted because of insufficient permissions",
            )

    return permission_checker


def check_roles(required_roles: list[str]):
    """
    Check if the current user has the required role.

    Args:
        required_roles (list[str]): The roles required to perform an action.

    Returns:
        function: A role checker function that raises an HTTPException if the user lacks the required role.
    """

    def role_checker(payload: dict = Depends(validate_token)):
        user_roles = payload.get("roles", [])
        # Check if the user has the required role, match the role name, only one role is required
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted because of insufficient roles",
            )

    return role_checker
