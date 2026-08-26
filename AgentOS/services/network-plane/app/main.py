from fastapi import FastAPI
import logging
from app.routers import mcp_registry, mcp_proxy

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AgentOS Network Plane",
    description="Handles MCP tool discovery, proxying, and governance checks."
)

app.include_router(mcp_registry.router)
app.include_router(mcp_proxy.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "network-plane"}
