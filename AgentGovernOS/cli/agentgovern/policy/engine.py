"""
Policy Engine — evaluates ABOM against bundled or custom policy rule packs.

Rules are defined as JSON files in agentgovern/policy/bundles/.
Each rule has: id, name, description, severity, check_fn_name, params.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentgovern.scanner.manifest import AgentDefinition
    from agentgovern.scanner.codeprint import CodeprintScanResult

# Built-in bundles ship with the package
BUNDLES_DIR = Path(__file__).parent / "bundles"


@dataclass
class PolicyViolation:
    """A single policy rule violation."""

    rule_id: str
    rule_name: str
    severity: str          # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    agent_code: str | None # None for project-level rules
    message: str
    suggestion: str
    source_file: str | None = None


@dataclass
class PolicyCheckResult:
    """Result of running all policy rules against the ABOM."""

    violations: list[PolicyViolation] = field(default_factory=list)
    rules_checked: int = 0
    bundle_name: str = "default"
    passed: bool = True

    def add(self, v: PolicyViolation) -> None:
        self.violations.append(v)
        if v.severity in {"HIGH", "CRITICAL"}:
            self.passed = False

    @property
    def by_severity(self) -> dict[str, list[PolicyViolation]]:
        result: dict[str, list[PolicyViolation]] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for v in self.violations:
            result.setdefault(v.severity, []).append(v)
        return result


def list_bundles -> list[str]:
    """Return names of all available policy bundles."""
    if not BUNDLES_DIR.exists:
        return []
    return [p.stem for p in BUNDLES_DIR.glob("*.json")]


def _load_bundle(bundle_name: str) -> dict[str, Any]:
    """Load a policy bundle JSON file.  Raises FileNotFoundError if not found."""
    # Check built-in bundles first
    builtin = BUNDLES_DIR / f"{bundle_name}.json"
    if builtin.exists:
        return json.loads(builtin.read_text(encoding="utf-8"))
    # Try as absolute path
    custom = Path(bundle_name)
    if custom.exists:
        return json.loads(custom.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Policy bundle '{bundle_name}' not found. Run `agentgovern policy list` to see available bundles.")


# ── Built-in rule implementations ─────────────────────────────────────────

def _rule_all_agents_have_tiers(
    agents: list["AgentDefinition"],
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    for agent in agents:
        if not agent.tier:
            result.add(PolicyViolation(
                rule_id=rule["id"],
                rule_name=rule["name"],
                severity=rule["severity"],
                agent_code=agent.code,
                message=f"Agent '{agent.code}' has no tier assigned.",
                suggestion="Add 'tier: T1|T2|T3|T4' to the agent definition in agentgovern.yaml",
                source_file=agent.source_file,
            ))


def _rule_all_agents_have_authority_limit(
    agents: list["AgentDefinition"],
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    for agent in agents:
        if agent.authority_limit is None:
            result.add(PolicyViolation(
                rule_id=rule["id"],
                rule_name=rule["name"],
                severity=rule["severity"],
                agent_code=agent.code,
                message=f"Agent '{agent.code}' has no authority_limit — it operates without a spending ceiling.",
                suggestion="Add 'authority_limit: <value>' to the agent definition.",
                source_file=agent.source_file,
            ))


def _rule_no_wildcard_actions(
    agents: list["AgentDefinition"],
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    wildcards = {"*", "all", "any"}
    for agent in agents:
        found = {a for a in agent.allowed_actions if a.lower in wildcards}
        if found:
            result.add(PolicyViolation(
                rule_id=rule["id"],
                rule_name=rule["name"],
                severity=rule["severity"],
                agent_code=agent.code,
                message=f"Agent '{agent.code}' uses wildcard actions: {sorted(found)}. This grants unrestricted capabilities.",
                suggestion="Replace wildcards with an explicit allowlist of actions.",
                source_file=agent.source_file,
            ))


def _rule_no_hardcoded_secrets(
    codeprint: "CodeprintScanResult | None",
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    if codeprint is None:
        return
    for secret in codeprint.secret_detections:
        result.add(PolicyViolation(
            rule_id=rule["id"],
            rule_name=rule["name"],
            severity=rule["severity"],
            agent_code=None,
            message=f"Hardcoded {secret.secret_type} detected at {secret.file}:{secret.line} ({secret.snippet})",
            suggestion="Move secrets to environment variables or a secrets manager (e.g., .env file, AWS Secrets Manager).",
            source_file=secret.file,
        ))


def _rule_max_authority_per_tier(
    agents: list["AgentDefinition"],
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    ceilings: dict[str, float] = rule.get("params", {}).get("ceilings", {})
    for agent in agents:
        if agent.tier and agent.authority_limit is not None:
            ceiling = ceilings.get(agent.tier)
            if ceiling is not None and agent.authority_limit > float(ceiling):
                result.add(PolicyViolation(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    severity=rule["severity"],
                    agent_code=agent.code,
                    message=(
                        f"Agent '{agent.code}' authority_limit ({agent.authority_limit:,.2f}) "
                        f"exceeds the {agent.tier} ceiling ({ceiling:,.2f}) defined by policy."
                    ),
                    suggestion=f"Lower authority_limit to at most {ceiling:,.2f} for tier {agent.tier}.",
                    source_file=agent.source_file,
                ))


def _rule_require_denied_actions(
    agents: list["AgentDefinition"],
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    for agent in agents:
        if not agent.denied_actions:
            result.add(PolicyViolation(
                rule_id=rule["id"],
                rule_name=rule["name"],
                severity=rule["severity"],
                agent_code=agent.code,
                message=f"Agent '{agent.code}' has no denied_actions defined — there is no explicit blocklist.",
                suggestion="Add 'denied_actions: [...]' to explicitly block dangerous operations.",
                source_file=agent.source_file,
            ))


def _rule_require_platform_bindings(
    agents: list["AgentDefinition"],
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    for agent in agents:
        if not agent.platform_bindings:
            result.add(PolicyViolation(
                rule_id=rule["id"],
                rule_name=rule["name"],
                severity=rule["severity"],
                agent_code=agent.code,
                message=f"Agent '{agent.code}' has no platform_bindings — it is not scoped to any system.",
                suggestion="Add 'platform_bindings: [SAP_S4HANA, ...]' to constrain where the agent can operate.",
                source_file=agent.source_file,
            ))


def _rule_at_least_one_agent(
    agents: list["AgentDefinition"],
    result: PolicyCheckResult,
    rule: dict[str, Any],
) -> None:
    if not agents:
        result.add(PolicyViolation(
            rule_id=rule["id"],
            rule_name=rule["name"],
            severity=rule["severity"],
            agent_code=None,
            message="No agents were found in agentgovern.yaml. Manifest appears empty.",
            suggestion="Add at least one agent definition to the manifest.",
        ))


# ── Rule dispatcher ────────────────────────────────────────────────────────

RULE_HANDLERS = {
    "REQUIRE_TIERING": _rule_all_agents_have_tiers,
    "AUTHORITY_LIMIT_SET": _rule_all_agents_have_authority_limit,
    "NO_WILDCARD_ACTIONS": _rule_no_wildcard_actions,
    "NO_HARDCODED_SECRETS": _rule_no_hardcoded_secrets,
    "MAX_AUTHORITY_PER_TIER": _rule_max_authority_per_tier,
    "REQUIRE_DENIED_ACTIONS": _rule_require_denied_actions,
    "REQUIRE_PLATFORM_BINDINGS": _rule_require_platform_bindings,
    "AT_LEAST_ONE_AGENT": _rule_at_least_one_agent,
}


def run_policy_checks(
    agents: list["AgentDefinition"],
    codeprint: "CodeprintScanResult | None" = None,
    bundle_name: str = "default",
) -> PolicyCheckResult:
    """
    Run all rules from the specified bundle against the agent list.
    Returns a PolicyCheckResult with all violations.
    """
    result = PolicyCheckResult(bundle_name=bundle_name)

    try:
        bundle = _load_bundle(bundle_name)
    except FileNotFoundError as exc:
        result.add(PolicyViolation(
            rule_id="BUNDLE_NOT_FOUND",
            rule_name="Bundle Load Error",
            severity="HIGH",
            agent_code=None,
            message=str(exc),
            suggestion="Check the bundle name or path. Use `agentgovern policy list` to see available bundles.",
        ))
        return result

    rules = bundle.get("rules", [])
    result.rules_checked = len(rules)

    for rule in rules:
        rule_id = rule.get("check")
        handler = RULE_HANDLERS.get(rule_id)

        if handler is None:
            continue

        # Route to the right handler signature
        if rule_id == "NO_HARDCODED_SECRETS":
            handler(codeprint, result, rule)  # type: ignore[call-arg]
        elif rule_id == "AT_LEAST_ONE_AGENT":
            handler(agents, result, rule)  # type: ignore[call-arg]
        else:
            handler(agents, result, rule)  # type: ignore[call-arg]

    return result
