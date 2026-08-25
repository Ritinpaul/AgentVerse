import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Swarm(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    description: str | None = None
    manager_agent_id: str
    worker_agent_ids: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SwarmCreate(BaseModel):
    tenant_id: str
    name: str
    description: str | None = None
    manager_agent_id: str
    worker_agent_ids: list[str] = []
