from app.db.base_class import Base  # noqa: F401

# Import all models here for Alembic metadata autogeneration
from app.models.agent_listing import AgentListing, AgentVersion  # noqa: F401, E402
from app.models.mcp_server_listing import MCPServerListing  # noqa: F401, E402
