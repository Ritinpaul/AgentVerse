import asyncio
import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.routers import execute
from app.worker import listen_for_events
from app.sandbox.terminal_bridge import terminal_manager

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AgentOS Execution Plane",
    description="Handles sandboxed execution of agents."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listen_for_events())

app.include_router(execute.router)

@app.websocket("/ws/terminal/{agent_id}")
async def root_terminal_websocket(websocket: WebSocket, agent_id: str):
    """Direct root alias for WebSocket PTY terminal session."""
    await terminal_manager.handle_connection(agent_id, websocket)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "execution-plane"}

