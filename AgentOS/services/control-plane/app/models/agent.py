import uuid
from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class AgentBase(SQLModel):
    name: str = Field(index=True)
    description: str | None = None
    entrypoint: str
    env_vars: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))

class Agent(AgentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="STOPPED") # STOPPED, RUNNING, SUSPENDED, TERMINATED, FAILED

class AgentRead(AgentBase):
    id: uuid.UUID
    status: str
    created_at: datetime

class AgentCreate(AgentBase):
    pass
