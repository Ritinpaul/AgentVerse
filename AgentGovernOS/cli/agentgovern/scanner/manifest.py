"""
Manifest Parser — reads and validates agentgovern.yaml files.

Supports both single-file and recursive discovery across a project tree.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Manifest schema (what a valid agentgovern.yaml looks like) ──────────────

REQUIRED_AGENT_FIELDS = {"code", "name", "framework"}
VALID_TIERS = {"T0", "T1", "T2", "T3", "T4"}
VALID_FRAMEWORKS = {
    "crewai",
    "langchain",
    "langchain-core",
    "autogen",
    "pyautogen",
    "openai-agents",
    "llamaindex",
    "llama-index",
    "semantic-kernel",
    "google-adk",
    "custom",
}


@dataclass
class AgentDefinition:
    """Parsed representation of a single agent from agentgovern.yaml."""

    code: str
    name: str
    framework: str
    tier: str | None = None
    authority_limit: float | None = None
    currency: str = "USD"
    allowed_actions: list[str] = field(default_factory=list)
    denied_actions: list[str] = field(default_factory=list)
    platform_bindings: list[str] = field(default_factory=list)
    risk_tolerance: str = "medium"
    source_file: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ManifestParseResult:
    """Result of parsing one agentgovern.yaml file."""

    path: Path
    project: str
    version: str
    agents: list[AgentDefinition]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def _parse_agent(raw: dict[str, Any], source_file: str) -> tuple[AgentDefinition | None, list[str]]:
    """Parse a single agent dict from the manifest.  Returns (agent, errors)."""
    errors: list[str] = []

    missing = REQUIRED_AGENT_FIELDS - raw.keys
    if missing:
        errors.append(f"Agent is missing required fields: {sorted(missing)}")
        return None, errors

    tier = raw.get("tier")
    if tier and tier not in VALID_TIERS:
        errors.append(f"Agent '{raw['code']}' has invalid tier '{tier}'. Must be one of {sorted(VALID_TIERS)}")

    framework = raw.get("framework", "").lower.replace("_", "-")
    if framework not in VALID_FRAMEWORKS:
        # Just a warning — unknown frameworks are not errors
        pass  # Handled at caller level as warning

    authority = raw.get("authority_limit")
    if authority is not None and not isinstance(authority, (int, float)):
        errors.append(f"Agent '{raw['code']}' authority_limit must be a number, got {type(authority).__name__}")
        authority = None

    return AgentDefinition(
        code=raw["code"],
        name=raw["name"],
        framework=framework,
        tier=tier,
        authority_limit=float(authority) if authority is not None else None,
        currency=raw.get("currency", "USD"),
        allowed_actions=raw.get("allowed_actions", []),
        denied_actions=raw.get("denied_actions", []),
        platform_bindings=raw.get("platform_bindings", []),
        risk_tolerance=raw.get("risk_tolerance", "medium"),
        source_file=source_file,
        raw=raw,
    ), errors


def parse_manifest(path: Path) -> ManifestParseResult:
    """Parse a single agentgovern.yaml file and return structured result."""
    errors: list[str] = []
    warnings: list[str] = []
    agents: list[AgentDefinition] = []

    if not path.exists:
        return ManifestParseResult(
            path=path, project="unknown", version="1.0",
            agents=[], errors=[f"File not found: {path}"]
        )

    try:
        raw_content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_content)
    except yaml.YAMLError as exc:
        return ManifestParseResult(
            path=path, project="unknown", version="1.0",
            agents=[], errors=[f"YAML parse error: {exc}"]
        )

    if not isinstance(data, dict):
        return ManifestParseResult(
            path=path, project="unknown", version="1.0",
            agents=[], errors=["Manifest must be a YAML mapping at the top level"]
        )

    project = data.get("project", path.parent.name)
    version = str(data.get("version", "1.0"))

    raw_agents = data.get("agents", [])
    if not raw_agents:
        warnings.append("No agents defined in manifest")

    for i, raw_agent in enumerate(raw_agents):
        if not isinstance(raw_agent, dict):
            errors.append(f"agents[{i}] must be a mapping, got {type(raw_agent).__name__}")
            continue

        agent, agent_errors = _parse_agent(raw_agent, str(path))
        errors.extend(agent_errors)

        if agent:
            frame = agent.framework
            if frame not in VALID_FRAMEWORKS:
                warnings.append(
                    f"Agent '{agent.code}' uses unknown framework '{frame}'. "
                    f"Known frameworks: {sorted(VALID_FRAMEWORKS)}"
                )
            if agent.tier is None:
                warnings.append(f"Agent '{agent.code}' has no tier assigned")
            if agent.authority_limit is None:
                warnings.append(f"Agent '{agent.code}' has no authority_limit — add one to enable governance")
            agents.append(agent)

    return ManifestParseResult(
        path=path,
        project=project,
        version=version,
        agents=agents,
        errors=errors,
        warnings=warnings,
    )


def discover_manifests(root: Path) -> list[Path]:
    """Walk `root` recursively and return all agentgovern.yaml paths found."""
    return [
        p for p in root.rglob("agentgovern.yaml")
        if not any(part.startswith(".") for part in p.parts)
        and ".venv" not in p.parts
        and "node_modules" not in p.parts
        and "__pycache__" not in p.parts
    ]
