from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import select
from sqlmodel import Session
from fastapi import (
    Depends,
    Header,
    Security,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from src.api.core.response import api_response
from src.api.models import User

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
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict,
    refresh: Optional[bool] = False,
    expires: Optional[timedelta] = None,
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


def is_authenticated(authorization: Optional[str] = Header(None)):
    """
    Extract user from Bearer token.
    Return None if token is missing or invalid.
    """
    if not authorization:
        return None  # No token means offline or guest user

    # Expect format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},  # verifies expiration
        )
        user = payload.get("user")
        return user
    except JWTError:
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

    except JWTError as e:
        print(e)
        return api_response(status.HTTP_401_UNAUTHORIZED, "Invalid token", data=str(e))


def require_admin(user: dict = Depends(require_signin)):
    roles: List[str] = user.get("roles", [])
    if "root" not in roles:
        api_response(status.HTTP_403_FORBIDDEN, "Root User only")
    return user


def require_permission(*permissions):
    # Flatten permissions - handle both requirePermission("a", "b") and requirePermission(["a", "b"])
    flat_permissions: List[str] = []
    for p in permissions:
        if isinstance(p, list):
            flat_permissions.extend(p)
        else:
            flat_permissions.append(p)

    def permission_checker(user: dict = Depends(require_signin)):
        user_permissions: List[str] = user.get("permissions", [])

        # ✅ system:* always passes
        if "system:*" in user_permissions:
            return user

        # ✅ Check for wildcard permissions (e.g., shop:* matches shop:view, shop:create, etc.)
        for required_perm in flat_permissions:
            # Exact match
            if required_perm in user_permissions:
                return user

            # Check if user has wildcard for this resource (e.g., user has shop:* and route needs shop:view)
            if ":" in required_perm:
                resource = required_perm.split(":")[0]
                if f"{resource}:*" in user_permissions:
                    return user

            # Check if route requires wildcard and user has any permission for that resource
            # (e.g., route needs shop:* and user has shop:view)
            if required_perm.endswith(":*"):
                resource = required_perm.replace(":*", "")
                if any(up.startswith(f"{resource}:") for up in user_permissions):
                    return user

        # ❌ no match → deny
        print(f"Permission denied for user: {user.get('email')}")
        print(f"  Required: {flat_permissions}")
        print(f"  User has: {user_permissions}")
        api_response(status.HTTP_403_FORBIDDEN, f"Permission denied. Required: {flat_permissions}, You have: {user_permissions}")

    return permission_checker
