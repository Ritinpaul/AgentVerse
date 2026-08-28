"""
Authority Analyser — cross-references agent definitions with their tool
access to identify authority mismatches and uncontrolled agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentgovern.scanner.manifest import AgentDefinition

# ── Tier authority ceiling map (in USD equivalent) ─────────────────────────
# These are the maximum authority limits each tier is allowed to have.
TIER_AUTHORITY_CEILINGS: dict[str, float] = {
    "T0": float("inf"),   # Executive tier — unlimited (requires additional approval)
    "T1": 1_000_000.0,    # Senior management
    "T2": 100_000.0,      # Management
    "T3": 10_000.0,       # Operational
    "T4": 500.0,          # Restricted / intern level
}

# Tools that are considered high-privilege
HIGH_PRIVILEGE_TOOLS = {
    "wire_transfer",
    "delete_records",
    "terminate_employee",
    "modify_salary",
    "admin_override",
    "grant_permissions",
    "escalate_all",
    "mass_send",
    "purge_data",
}

# Wildcard indicators — agents that can do anything
WILDCARD_ACTIONS = {"*", "all", "any", ".*"}


@dataclass
class AuthorityViolation:
    """An authority-related violation for a single agent."""

    agent_code: str
    violation_type: str  # e.g., "AUTHORITY_EXCEEDS_TIER", "MISSING_AUTHORITY_LIMIT"
    severity: str        # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    message: str
    suggestion: str


@dataclass
class AuthorityAnalysisResult:
    """Result of authority analysis across all agents."""

    violations: list[AuthorityViolation] = field(default_factory=list)
    risk_scores: dict[str, str] = field(default_factory=dict)  # agent_code → risk level

    @property
    def has_critical(self) -> bool:
        return any(v.severity == "CRITICAL" for v in self.violations)


def analyse_authority(agents: list["AgentDefinition"]) -> AuthorityAnalysisResult:
    """
    Perform authority analysis on a list of parsed agent definitions.
    Returns violations and per-agent risk scores.
    """
    result = AuthorityAnalysisResult

    for agent in agents:
        violations_for_agent: list[AuthorityViolation] = []
        risk_level = "LOW"

        # ── 1. Check: authority_limit is set ──────────────────────────────
        if agent.authority_limit is None:
            violations_for_agent.append(AuthorityViolation(
                agent_code=agent.code,
                violation_type="MISSING_AUTHORITY_LIMIT",
                severity="HIGH",
                message=f"Agent '{agent.code}' has no authority_limit defined — it is uncontrolled.",
                suggestion="Add 'authority_limit: <value>' to the agent definition in agentgovern.yaml",
            ))
            risk_level = "HIGH"

        # ── 2. Check: authority doesn't exceed tier ceiling ───────────────
        if agent.authority_limit is not None and agent.tier:
            ceiling = TIER_AUTHORITY_CEILINGS.get(agent.tier, 0.0)
            if agent.authority_limit > ceiling:
                violations_for_agent.append(AuthorityViolation(
                    agent_code=agent.code,
                    violation_type="AUTHORITY_EXCEEDS_TIER",
                    severity="HIGH",
                    message=(
                        f"Agent '{agent.code}' authority_limit ({agent.authority_limit:,.2f} {agent.currency}) "
                        f"exceeds the ceiling for tier {agent.tier} ({ceiling:,.2f})."
                    ),
                    suggestion=f"Lower the authority_limit or upgrade tier. {agent.tier} max = {ceiling:,.2f}",
                ))
                risk_level = "HIGH"

        # ── 3. Check: wildcard tool access ────────────────────────────────
        allowed = {a.lower for a in agent.allowed_actions}
        if allowed & WILDCARD_ACTIONS:
            violations_for_agent.append(AuthorityViolation(
                agent_code=agent.code,
                violation_type="WILDCARD_TOOL_ACCESS",
                severity="CRITICAL",
                message=f"Agent '{agent.code}' has wildcard tool access ('{allowed & WILDCARD_ACTIONS}'). This grants unrestricted capabilities.",
                suggestion="Replace wildcard with an explicit list of allowed actions.",
            ))
            risk_level = "CRITICAL"

        # ── 4. Check: high-privilege tools ────────────────────────────────
        high_priv_used = {a for a in agent.allowed_actions if a.lower in HIGH_PRIVILEGE_TOOLS}
        if high_priv_used:
            tier_ok = agent.tier in {"T0", "T1"} if agent.tier else False
            sev = "MEDIUM" if tier_ok else "HIGH"
            violations_for_agent.append(AuthorityViolation(
                agent_code=agent.code,
                violation_type="HIGH_PRIVILEGE_TOOLS",
                severity=sev,
                message=(
                    f"Agent '{agent.code}' has access to high-privilege tools: {sorted(high_priv_used)}. "
                    + ("Tier is adequate." if tier_ok else f"Tier {agent.tier or 'UNSET'} may be insufficient.")
                ),
                suggestion="Ensure high-privilege tools are only used by T0/T1 agents with explicit justification.",
            ))
            if sev == "HIGH" and risk_level == "LOW":
                risk_level = "MEDIUM"

        # ── 5. Check: no tier assigned ────────────────────────────────────
        if not agent.tier:
            violations_for_agent.append(AuthorityViolation(
                agent_code=agent.code,
                violation_type="MISSING_TIER",
                severity="MEDIUM",
                message=f"Agent '{agent.code}' has no tier assigned.",
                suggestion="Assign a tier (T0-T4) to enable authority ceiling checks.",
            ))
            if risk_level == "LOW":
                risk_level = "MEDIUM"

        # Set overall risk score considering number of violations
        if len(violations_for_agent) >= 3:
            risk_level = "HIGH"

        result.violations.extend(violations_for_agent)
        result.risk_scores[agent.code] = risk_level

    return result
