import logging
import os
from typing import Any

from jose import JWTError, jwt
from middleware.auth import (  # noqa: F401
    ROLE_ADMIN,
    ROLE_AGENT,
    ROLE_AUDITOR,
    ROLE_DEVELOPER,
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_READ,
    ROLE_TRIAGE,
    ROLE_WRITE,
    require_admin,
    require_auditor,
    require_operator,
    require_read,
    require_roles,
    require_write,
)

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "change-me-in-production"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


class AuthService:
    @staticmethod
    def get_secret_key() -> str:
        return os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "change-me-in-production"

    @staticmethod
    def validate_token(token: str) -> dict[str, Any] | None:
        """
        Validates a JWT token and returns the payload.
        """
        try:
            secret = AuthService.get_secret_key()
            payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"JWT Validation Error: {e}")
            return None

    @staticmethod
    def get_user_roles(payload_or_user_id: Any) -> list[str]:
        """
        Extracts user roles from JWT payload or looks up user context.
        Defaults to ['user'] if no specific role is assigned.
        """
        if isinstance(payload_or_user_id, dict):
            roles = payload_or_user_id.get("roles") or payload_or_user_id.get("role")
            if roles:
                return [roles] if isinstance(roles, str) else list(roles)
        return ["user"]
