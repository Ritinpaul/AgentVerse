import logging
import os

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from services.auth import AuthService

logger = logging.getLogger(__name__)

# Public endpoints that do not require authentication
PUBLIC_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/oidc/callback",
    "/health",
    "/metrics",
    "/favicon.ico"
)

class RBACMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Skip RBAC for public routes
        path = request.url.path
        if path == "/" or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
            return await call_next(request)

        # 2. Extract Authorization header or API Key
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")
        
        app_env = os.getenv("APP_ENV", "development")
        admin_key = os.getenv("ADMIN_API_KEY", "")

        # Allow admin API key header
        if api_key and (api_key == admin_key or app_env in ("development", "test")):
            request.state.user = {"sub": "api_key_user", "roles": ["admin"]}
            return await call_next(request)

        # Require Bearer token if no valid API key
        if not auth_header or not auth_header.startswith("Bearer "):
            # In development/test environment, default to system admin payload
            if app_env in ("development", "test"):
                request.state.user = {"sub": "dev_user", "roles": ["admin"]}
                return await call_next(request)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials required"
            )
            
        token = auth_header.split(" ")[1]
        payload = AuthService.validate_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials"
            )
        
        request.state.user = payload
        return await call_next(request)
