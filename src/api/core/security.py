from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import select
from sqlmodel import Session
from fastapi import (
    Depends,
    Security,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from src.api.core.response import api_response
from src.api.models.usersModel import User

ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


## get user
def exist_user(db: Session, email: str):
    user = db.exec(select(User).where(User.email == email)).first()
    return user


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict,
    refresh: Optional[bool] = False,
    expires: timedelta = None,
):

    if refresh:
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        expire = datetime.now(timezone.utc) + (
            expires or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

    payload = {
        "user": user_data,
        "exp": expire,
        "refresh": refresh,
    }
    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_token(
    token: str,
) -> Optional[Dict]:
    try:
        decode = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},  # Ensure expiration is verified
        )

        return decode

    except JWTError as e:
        print(f"Token decoding failed: {e}")
        return None


def require_signin(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer()),
) -> Dict:
    token = credentials.credentials  # Extract token from Authorization header

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user = payload.get("user")

        if user is None:
            api_response(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid token: no user data",
            )

        if payload.get("refresh") is True:
            api_response(
                401,
                "Refresh token is not allowed for this route",
            )

        return user  # contains {"email": ..., "id": ...}

    except JWTError:
        api_response(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )


def require_admin(
    user: dict = Depends(require_signin),
):
    try:
        if user.get("role") != "admin":
            api_response(
                status.HTTP_403_FORBIDDEN,
                "Access denied: Admins only",
            )

        return user  # user info with "email", "id", "role"

    except JWTError:
        api_response(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )


def require_permission(permission: str):
    def permission_checker(
        user: dict = Depends(require_signin),
    ):
        role = user.get("role")
        permissions = user.get("permissions", [])
        if not role:
            api_response(403, "Permission denied")

        # Allow all if "all" is in permissions
        if "all" in permissions or permission in permissions:
            return user

        api_response(403, "Permission denied")

    return permission_checker
