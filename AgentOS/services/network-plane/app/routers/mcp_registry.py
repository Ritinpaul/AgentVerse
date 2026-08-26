from fastapi import APIRouter
from app.services.mcp_discoverer import load_registry

router = APIRouter(prefix="/registry", tags=["registry"])

@router.get("/servers")
def list_servers():
    """
    Returns the list of available MCP servers that agents can use.
    """
    return {"servers": load_registry()}
