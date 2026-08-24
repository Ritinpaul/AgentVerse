from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import conversation, workspace, snapshots, webhooks, pubsub, telemetry

app = FastAPI(
    title="AgentOS State Plane",
    description="Manages agent conversational state, memory, and workspace file I/O."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversation.router)
app.include_router(workspace.router)
app.include_router(snapshots.router)
app.include_router(webhooks.router)
app.include_router(pubsub.router)
app.include_router(telemetry.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "state-plane"}
