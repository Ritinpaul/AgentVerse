import uuid
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# A context variable to store the current organization ID
_current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("current_tenant_id", default=None)
_current_data_region: ContextVar[str] = ContextVar("current_data_region", default="us-east-1")

def get_current_tenant_id() -> uuid.UUID | None:
    return _current_tenant_id.get()

def get_current_data_region() -> str:
    return _current_data_region.get()

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extremely simplified tenant extraction for # We can extract the tenant from a JWT token, or a header like X-Organization-ID
        # We assume X-Organization-ID for simplicity before full OIDC is integrated
        org_id_str = request.headers.get("X-Organization-ID")
        region_str = request.headers.get("X-Data-Region", "us-east-1")
        org_id = None
        if org_id_str:
            try:
                org_id = uuid.UUID(org_id_str)
            except ValueError:
                pass
        
        token = _current_tenant_id.set(org_id)
        region_token = _current_data_region.set(region_str)
        try:
            response = await call_next(request)
        finally:
            _current_tenant_id.reset(token)
            _current_data_region.reset(region_token)
        return response
