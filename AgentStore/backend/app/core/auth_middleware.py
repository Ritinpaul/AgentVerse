"""
Authentication & RBAC Middleware for AgentStore Backend
Supports:
1. Bearer JWT tokens (Supabase Auth / AgentGovernOS tokens) using SUPABASE_JWT_SECRET / JWT_SECRET_KEY
2. Service-to-service X-API-Key header (NUUVIXX_API_KEY, NUUVIXX_ADMIN_KEY)
3. Role-Based Access Control (RBAC) & Builder Ownership Guard
"""

import os
from typing import Optional, List
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
import jwt


class UserIdentity(BaseModel):
    user_id: str
    org_id: str
    role: str = "builder"  # "builder", "admin", "owner", "viewer", "service"
    is_service: bool = False


def get_jwt_secret() -> str:
    return (
        os.getenv("SUPABASE_JWT_SECRET")
        or os.getenv("JWT_SECRET_KEY")
        or os.getenv("JWT_SECRET")
        or "dev-jwt-secret-change-in-prod"
    )


def get_valid_api_keys() -> set[str]:
    keys = set()
    for env_var in ["NUUVIXX_API_KEY", "NUUVIXX_ADMIN_KEY", "AGENTSTORE_API_KEYS"]:
        val = os.getenv(env_var, "").strip()
        if val:
            for k in val.split(","):
                if k.strip():
                    keys.add(k.strip())
    if not keys:
        keys.add("dev-nuuvixx-svc-key-2026")
        keys.add("dev-admin-key-2026")
    return keys


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_user_org: Optional[str] = Header(None, alias="X-User-Org"),
) -> UserIdentity:
    """
    Authenticate request via X-API-Key or Bearer JWT token.
    Raises 401 Unauthorized if invalid or missing.
    """
    # 1. Check Service API Key
    if x_api_key:
        valid_keys = get_valid_api_keys()
        if x_api_key in valid_keys:
            admin_key = os.getenv("NUUVIXX_ADMIN_KEY", "dev-admin-key-2026").strip()
            if x_user_org:
                return UserIdentity(
                    user_id=f"service-{x_user_org}",
                    org_id=x_user_org,
                    role="builder",
                    is_service=False,
                )
            role = "admin" if x_api_key == admin_key else "service"
            return UserIdentity(
                user_id="service-account",
                org_id="nuuvixx",
                role=role,
                is_service=True,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-API-Key header provided",
        )


    # 2. Check Bearer Token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        secret = get_jwt_secret()
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256", "RS256"],
                options={"verify_aud": False, "verify_iss": False},
            )
            user_id = str(payload.get("sub") or payload.get("user_id") or "anon-user")
            org_id = str(payload.get("org_id") or payload.get("user_metadata", {}).get("org_id") or "community")
            role = str(payload.get("role") or payload.get("user_metadata", {}).get("role") or "builder")
            return UserIdentity(
                user_id=user_id,
                org_id=org_id,
                role=role,
                is_service=False,
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
            )
        except jwt.InvalidTokenError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(err)}",
            )

    # 3. Allow anonymous dev mode ONLY if explicitly enabled
    allow_dev = os.getenv("ALLOW_DEV_ANONYMOUS", "false").lower() == "true"
    if allow_dev:
        return UserIdentity(
            user_id="dev-anon",
            org_id="nuuvixx",
            role="admin",
            is_service=True,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication credentials. Provide 'Authorization: Bearer <token>' or 'X-API-Key' header.",
    )


def require_roles(allowed_roles: List[str]):
    """Enforces that the current user has one of the allowed roles."""
    def role_checker(user: UserIdentity = Depends(get_current_user)) -> UserIdentity:
        if user.role not in allowed_roles and not user.is_service:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of roles: {allowed_roles}. Current role: {user.role}",
            )
        return user
    return role_checker
