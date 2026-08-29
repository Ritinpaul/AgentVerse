from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime
from app.db.base_class import Base

class MCPServerListing(Base):
    __tablename__ = "mcp_server_listings"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)  # format: builder/server-name
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)
    builder_id = Column(String, index=True, nullable=False)
    transport = Column(String, default="stdio")  # stdio, sse, websocket
    command = Column(String, nullable=True)
    args = Column(JSON, default=list)
    env_keys = Column(JSON, default=list)  # list of environment variable names required
    tags = Column(JSON, default=list)
    current_version = Column(String, nullable=False, default="0.1.0")
    status = Column(String, default="active")
    trust_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
