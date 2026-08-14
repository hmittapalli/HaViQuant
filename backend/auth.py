import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("HAVIQ_AUTH_EXPIRE_MINUTES", "480"))

# IMPORTANT:
# Set HAVIQ_AUTH_SECRET on Render.
# This development fallback is only for local testing.
JWT_SECRET = os.getenv(
    "HAVIQ_AUTH_SECRET",
    "CHANGE_THIS_LOCAL_SECRET_BEFORE_PRODUCTION"
)

AUTH_USERNAME = os.getenv("HAVIQ_AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("HAVIQ_AUTH_PASSWORD", "CHANGE_THIS_LOCAL_PASSWORD")


security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def authenticate_user(username: str, password: str) -> bool:
    return (
        username == AUTH_USERNAME
        and password == AUTH_PASSWORD
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        username = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if username != AUTH_USERNAME:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return username

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
