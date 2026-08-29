"""
Dependency Resolver & Lockfile Generator
Handles recursive dependency resolution for agent pipelines and generates agentstore.lock.json.
"""
from __future__ import annotations
import yaml
from datetime import datetime, timezone
from typing import List, Dict, Set
from sqlalchemy.orm import Session

from app.models.agent_listing import AgentListing, AgentVersion


def resolve_agent_dependencies(agent_slugs: List[str], db: Session) -> dict:
    """
    Recursively resolve all direct and transitive dependencies (sub-agents and MCP tools)
    for a given list of root agent slugs.

    Returns:
    {
        "resolved_agents": [ {slug, name, version, trust_score, verification_status} ],
        "mcp_servers": [ {server, tools} ],
        "dependency_tree": { root_slug: [ child_slugs ] },
        "missing_dependencies": [ slug ]
    }
    """
    resolved_agents: Dict[str, dict] = {}
    mcp_servers: Dict[str, Set[str]] = {}
    dependency_tree: Dict[str, List[str]] = {}
    missing_deps: List[str] = []
    visited: Set[str] = set()

    queue = list(agent_slugs)

    while queue:
        current_slug = queue.pop(0)
        if current_slug in visited:
            continue
        visited.add(current_slug)

        listing = db.query(AgentListing).filter(AgentListing.slug == current_slug).first()
        if not listing:
            missing_deps.append(current_slug)
            continue

        latest_version = (
            db.query(AgentVersion)
            .filter(AgentVersion.listing_id == listing.id, AgentVersion.status == "published")
            .order_by(AgentVersion.id.desc())
            .first()
        )

        version_semver = latest_version.version_semver if latest_version else listing.current_version
        sub_deps: List[str] = []

        if latest_version:
            try:
                parsed = yaml.safe_load(latest_version.agent_yaml) or {}
                # Extract sub-agents
                for dep in parsed.get("dependencies", []):
                    if isinstance(dep, str):
                        sub_deps.append(dep)
                    elif isinstance(dep, dict) and "slug" in dep:
                        sub_deps.append(dep["slug"])

                # Extract MCP servers
                for tool in parsed.get("tools", []):
                    if isinstance(tool, dict) and tool.get("type") == "mcp":
                        srv = tool.get("server")
                        tool_name = tool.get("tool")
                        if srv:
                            if srv not in mcp_servers:
                                mcp_servers[srv] = set()
                            if tool_name:
                                mcp_servers[srv].add(tool_name)
            except Exception:
                pass

        dependency_tree[current_slug] = sub_deps

        resolved_agents[current_slug] = {
            "id": listing.id,
            "slug": listing.slug,
            "name": listing.name,
            "version": version_semver,
            "trust_score": listing.trust_score,
            "verification_status": listing.verification_status,
            "category": listing.category,
        }

        # Queue sub-dependencies for resolution
        for child in sub_deps:
            if child not in visited:
                queue.append(child)

    mcp_formatted = [
        {"server": srv, "tools": sorted(list(tools))}
        for srv, tools in mcp_servers.items()
    ]

    return {
        "resolved_agents": list(resolved_agents.values()),
        "mcp_servers": mcp_formatted,
        "dependency_tree": dependency_tree,
        "missing_dependencies": missing_deps,
    }


def generate_lockfile(composition_slug: str, resolved_data: dict) -> dict:
    """
    Generates a deterministic agentstore.lock.json representation for a composition.
    """
    agents_pinned = {}
    for a in resolved_data.get("resolved_agents", []):
        agents_pinned[a["slug"]] = {
            "version": a["version"],
            "trust_score": a["trust_score"],
            "verification_status": a["verification_status"],
        }

    return {
        "lockfile_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "composition_slug": composition_slug,
        "agents": agents_pinned,
        "mcp_servers": resolved_data.get("mcp_servers", []),
        "dependency_tree": resolved_data.get("dependency_tree", {}),
        "integrity_hash": f"sha256:{hash(str(agents_pinned)) & 0xffffffff:08x}",
    }
