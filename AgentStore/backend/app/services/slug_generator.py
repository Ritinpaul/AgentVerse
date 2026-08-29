import re
from sqlalchemy.orm import Session
from app.models.agent_listing import AgentListing
from app.models.mcp_server_listing import MCPServerListing

def sanitize_part(text: str) -> str:
    # Convert to lowercase, replace whitespace and underscores with hyphens, remove non-alphanumeric/hyphen
    text = text.lower().strip()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^a-z0-9\-]', '', text)
    text = re.sub(r'\-+', '-', text).strip('-')
    return text or "agent"

def generate_agent_slug(builder_id: str, agent_name: str, db: Session) -> str:
    builder_part = sanitize_part(builder_id)
    agent_part = sanitize_part(agent_name)
    base_slug = f"{builder_part}/{agent_part}"
    
    slug = base_slug
    counter = 1
    while db.query(AgentListing).filter(AgentListing.slug == slug).first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

def generate_mcp_server_slug(builder_id: str, server_name: str, db: Session) -> str:
    builder_part = sanitize_part(builder_id)
    server_part = sanitize_part(server_name)
    base_slug = f"{builder_part}/{server_part}"
    
    slug = base_slug
    counter = 1
    while db.query(MCPServerListing).filter(MCPServerListing.slug == slug).first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug
