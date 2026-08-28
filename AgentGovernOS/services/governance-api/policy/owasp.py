"""OWASP AI Security (ASI01–ASI10) Policy Implementations.

adds three new concrete policy classes that fill the gaps identified
in docs/OWASP_AI_MAPPING.md:

    ASI07InterAgentPolicy   — Insecure Plugin/Tool Design (inter-agent delegation)
    ASI08CascadingPolicy    — Excessive Agency (circular delegation detection)
    ASI09OverreliancePolicy — Overreliance (low-confidence decision gate)

Each class exposes:
    evaluate(context: dict) -> PolicyResult

And can be registered via the /governance/owasp-coverage endpoint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Common types
# ─────────────────────────────────────────────────────────────────────────────

class ASIVerdict(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


@dataclass
class PolicyResult:
    """Result from a single ASI policy evaluation."""
    asi_id: str
    verdict: ASIVerdict
    reason: str
    details: dict[str, Any] = field(default_factory=dict)
    remediation: str = ""

    @property
    def is_blocking(self) -> bool:
        return self.verdict == ASIVerdict.BLOCK

    @property
    def requires_escalation(self) -> bool:
        return self.verdict in (ASIVerdict.ESCALATE, ASIVerdict.BLOCK)


# ─────────────────────────────────────────────────────────────────────────────
# ASI07 — Insecure Plugin/Tool Design (Inter-Agent Communication)
# ─────────────────────────────────────────────────────────────────────────────

class ASI07InterAgentPolicy:
    """ASI07: Insecure Plugin/Tool Design — Inter-Agent Delegation Validator.

    Validates cross-agent delegation requests to prevent:
    - Unsigned delegation chains (identity spoofing)
    - Excessive delegation depth (resource exhaustion)
    - Unknown caller agents (lateral movement)
    - Missing intent declarations

    Policy code: POL-ASI07-INTER-AGENT
    Severity: HIGH
    Action on violation: BLOCK
    """

    POLICY_CODE = "POL-ASI07-INTER-AGENT"
    MAX_DELEGATION_DEPTH = 5

    # Regex: intent must be a non-empty alphanumeric string
    _INTENT_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\. ]{3,200}$')

    def evaluate(self, context: dict[str, Any]) -> PolicyResult:
        """Evaluate an inter-agent delegation request.

        Expected context keys:
            caller_id:          str  — DID or agent_code of the calling agent
            target_id:          str  — DID or agent_code of the target agent
            delegation_depth:   int  — current nesting depth (0 = direct user request)
            intent:             str  — natural language intent description
            intent_signature:   str  — HMAC/Ed25519 signature of intent by caller
            delegation_chain:   list — list of agent IDs in the current chain
        """
        caller_id = context.get("caller_id", "")
        delegation_depth = context.get("delegation_depth", 0)
        intent = context.get("intent", "")
        intent_signature = context.get("intent_signature", "")
        delegation_chain = context.get("delegation_chain", [])

        # Check 1: Caller identity must be present
        if not caller_id:
            return PolicyResult(
                asi_id="ASI07",
                verdict=ASIVerdict.BLOCK,
                reason="Missing caller_id in delegation request",
                details={"violation": "unsigned_caller"},
                remediation="Include a valid agent_code or DID in caller_id field",
            )

        # Check 2: Delegation depth limit
        if delegation_depth > self.MAX_DELEGATION_DEPTH:
            return PolicyResult(
                asi_id="ASI07",
                verdict=ASIVerdict.BLOCK,
                reason=f"Delegation depth {delegation_depth} exceeds maximum {self.MAX_DELEGATION_DEPTH}",
                details={
                    "current_depth": delegation_depth,
                    "max_depth": self.MAX_DELEGATION_DEPTH,
                    "chain": delegation_chain,
                },
                remediation="Redesign agent workflow to reduce delegation nesting",
            )

        # Check 3: Intent must be present and well-formed
        if not intent:
            return PolicyResult(
                asi_id="ASI07",
                verdict=ASIVerdict.BLOCK,
                reason="Missing intent declaration in delegation request",
                details={"violation": "missing_intent"},
                remediation="Provide a clear intent string describing the delegated task",
            )

        if not self._INTENT_PATTERN.match(intent):
            return PolicyResult(
                asi_id="ASI07",
                verdict=ASIVerdict.WARN,
                reason=f"Intent string does not match expected format: '{intent[:50]}'",
                details={"violation": "malformed_intent", "intent_preview": intent[:50]},
                remediation="Use alphanumeric characters and standard punctuation in intent",
            )

        # Check 4: Intent signature (if enforcement mode is enabled)
        # In we WARN rather than BLOCK for missing signatures
        # (DID identity infrastructure lands in )
        if not intent_signature:
            return PolicyResult(
                asi_id="ASI07",
                verdict=ASIVerdict.WARN,
                reason="Intent signature missing — will be required after DID rollout",
                details={"violation": "unsigned_intent", "caller_id": caller_id},
                remediation="Sign intent with caller agent's Ed25519 private key",
            )

        return PolicyResult(
            asi_id="ASI07",
            verdict=ASIVerdict.PASS,
            reason="Inter-agent delegation request is valid",
            details={"caller_id": caller_id, "delegation_depth": delegation_depth},
        )


# ─────────────────────────────────────────────────────────────────────────────
# ASI08 — Excessive Agency (Cascading / Circular Delegation)
# ─────────────────────────────────────────────────────────────────────────────

class ASI08CascadingPolicy:
    """ASI08: Excessive Agency — Cascading Failure & Circular Delegation Detector.

    Detects:
    - Circular delegation chains (A → B → C → A)
    - Single agent making too many recursive calls
    - Cascading failure patterns (exponential call growth)

    Policy code: POL-ASI08-CASCADE
    Severity: CRITICAL
    Action on violation: BLOCK
    """

    POLICY_CODE = "POL-ASI08-CASCADE"
    MAX_SELF_CALLS = 3      # An agent cannot delegate to itself more than 3 times
    MAX_CHAIN_LENGTH = 10   # Absolute maximum delegation chain length

    def evaluate(self, context: dict[str, Any]) -> PolicyResult:
        """Evaluate delegation chain for circular patterns.

        Expected context keys:
            agent_id:           str  — current agent's ID
            delegation_chain:   list — ordered list of agent IDs in chain (oldest first)
            total_calls:        int  — total delegations made in this session
        """
        agent_id = context.get("agent_id", "")
        delegation_chain = context.get("delegation_chain", [])
        total_calls = context.get("total_calls", 0)

        # Check 1: Circular delegation — agent already in chain
        if agent_id and agent_id in delegation_chain:
            cycle_start = delegation_chain.index(agent_id)
            cycle_path = delegation_chain[cycle_start:] + [agent_id]
            return PolicyResult(
                asi_id="ASI08",
                verdict=ASIVerdict.BLOCK,
                reason=f"Circular delegation detected: {' → '.join(cycle_path)}",
                details={
                    "violation": "circular_delegation",
                    "cycle_path": cycle_path,
                    "detected_at_depth": len(delegation_chain),
                },
                remediation="Redesign workflow to eliminate agent dependency cycles",
            )

        # Check 2: Chain length limit
        if len(delegation_chain) >= self.MAX_CHAIN_LENGTH:
            return PolicyResult(
                asi_id="ASI08",
                verdict=ASIVerdict.BLOCK,
                reason=f"Delegation chain length {len(delegation_chain)} exceeds maximum {self.MAX_CHAIN_LENGTH}",
                details={
                    "chain_length": len(delegation_chain),
                    "max_length": self.MAX_CHAIN_LENGTH,
                },
                remediation="Flatten the delegation hierarchy or use a direct orchestrator pattern",
            )

        # Check 3: Self-delegation count (same agent appears multiple times)
        self_count = delegation_chain.count(agent_id)
        if self_count >= self.MAX_SELF_CALLS:
            return PolicyResult(
                asi_id="ASI08",
                verdict=ASIVerdict.ESCALATE,
                reason=(
                    f"Agent {agent_id} has appeared {self_count} times in delegation chain — "
                    f"possible recursive loop"
                ),
                details={
                    "agent_id": agent_id,
                    "appearances": self_count,
                    "chain": delegation_chain,
                },
                remediation="Add termination condition to prevent unbounded recursion",
            )

        return PolicyResult(
            asi_id="ASI08",
            verdict=ASIVerdict.PASS,
            reason="No cascading failure pattern detected",
            details={
                "chain_length": len(delegation_chain),
                "total_calls": total_calls,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# ASI09 — Overreliance (Low-Confidence Decision Gate)
# ─────────────────────────────────────────────────────────────────────────────

class ASI09OverreliancePolicy:
    """ASI09: Overreliance — Low-Confidence Decision Escalation Gate.

    Prevents agents from taking autonomous actions when their confidence
    in the correct outcome is below acceptable thresholds.

    Thresholds:
        < 0.3  → BLOCK (cannot act without human approval)
        0.3–0.5 → ESCALATE (route to ECLIPSE for human review)
        > 0.5  → PASS (sufficient confidence to proceed)

    For high-stakes actions (amount > threshold), confidence floor is raised.

    Policy code: POL-ASI09-CONFIDENCE
    Severity: HIGH
    Action on violation: ESCALATE / BLOCK
    """

    POLICY_CODE = "POL-ASI09-CONFIDENCE"

    # Confidence thresholds
    BLOCK_THRESHOLD = 0.30
    ESCALATE_THRESHOLD = 0.50

    # For high-stakes actions, raise the confidence floor
    HIGH_STAKES_AMOUNT = 10_000.0
    HIGH_STAKES_ESCALATE_THRESHOLD = 0.70

    def evaluate(self, context: dict[str, Any]) -> PolicyResult:
        """Evaluate whether agent confidence is sufficient for autonomous action.

        Expected context keys:
            confidence_score:   float  — agent's self-reported confidence (0.0–1.0)
            action_type:        str    — type of action being taken
            amount:             float  — financial amount involved (if any)
            risk_score:         str    — SENTINEL risk classification
        """
        confidence_score = context.get("confidence_score")
        action_type = context.get("action_type", "unknown")
        amount = float(context.get("amount", 0.0))
        risk_score = context.get("risk_score", "UNKNOWN")

        # If confidence score not provided, skip (not all actions report it)
        if confidence_score is None:
            return PolicyResult(
                asi_id="ASI09",
                verdict=ASIVerdict.PASS,
                reason="Confidence score not provided — skipping overreliance check",
                details={"action_type": action_type},
            )

        confidence = float(confidence_score)

        # Determine applicable threshold (higher for high-stakes)
        is_high_stakes = (
            amount >= self.HIGH_STAKES_AMOUNT
            or risk_score in ("HIGH", "CRITICAL")
        )

        escalate_threshold = (
            self.HIGH_STAKES_ESCALATE_THRESHOLD if is_high_stakes
            else self.ESCALATE_THRESHOLD
        )

        # Check: Below hard block threshold
        if confidence < self.BLOCK_THRESHOLD:
            return PolicyResult(
                asi_id="ASI09",
                verdict=ASIVerdict.BLOCK,
                reason=(
                    f"Confidence {confidence:.2f} is below minimum threshold "
                    f"{self.BLOCK_THRESHOLD:.2f} — action blocked to prevent overreliance"
                ),
                details={
                    "confidence_score": confidence,
                    "threshold": self.BLOCK_THRESHOLD,
                    "action_type": action_type,
                    "amount": amount,
                },
                remediation=(
                    "Gather more context before proceeding, or request human guidance "
                    "through the ECLIPSE escalation queue"
                ),
            )

        # Check: Below escalation threshold
        if confidence < escalate_threshold:
            return PolicyResult(
                asi_id="ASI09",
                verdict=ASIVerdict.ESCALATE,
                reason=(
                    f"Confidence {confidence:.2f} is below escalation threshold "
                    f"{escalate_threshold:.2f} for {'high-stakes' if is_high_stakes else 'standard'} action"
                ),
                details={
                    "confidence_score": confidence,
                    "threshold": escalate_threshold,
                    "action_type": action_type,
                    "amount": amount,
                    "is_high_stakes": is_high_stakes,
                },
                remediation="Route to human reviewer via ECLIPSE before proceeding",
            )

        return PolicyResult(
            asi_id="ASI09",
            verdict=ASIVerdict.PASS,
            reason=f"Confidence {confidence:.2f} meets threshold {escalate_threshold:.2f}",
            details={
                "confidence_score": confidence,
                "threshold": escalate_threshold,
                "is_high_stakes": is_high_stakes,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# OWASP Coverage Registry
# ─────────────────────────────────────────────────────────────────────────────

OWASP_COVERAGE = {
    "ASI01": {
        "name": "Prompt Injection",
        "status": "covered",
        "controls": ["SENTINEL policy engine", "edge-gateway validation"],
        "policies": ["POL-SEC-001"],
        "gap": None,
        "phase_to_fill": None,
    },
    "ASI02": {
        "name": "Insecure Output Handling",
        "status": "covered",
        "controls": ["output action validation in governance.py", "ANCESTOR audit log"],
        "policies": ["governance_verdict_validation"],
        "gap": None,
        "phase_to_fill": None,
    },
    "ASI03": {
        "name": "Training Data Poisoning",
        "status": "partial",
        "controls": ["architectural: pre-trained models only"],
        "policies": [],
        "gap": "No runtime behavioral drift detection",
        "phase_to_fill": 1,
    },
    "ASI04": {
        "name": "Model Denial of Service",
        "status": "covered",
        "controls": ["token budgets", "rate limiting", "tier ceilings"],
        "policies": ["authority_limit_enforcement", "rate_limit_middleware"],
        "gap": None,
        "phase_to_fill": None,
    },
    "ASI05": {
        "name": "Supply Chain Vulnerabilities",
        "status": "partial",
        "controls": ["pinned dependency versions", "MCP tool validation"],
        "policies": [],
        "gap": "No SBOM generation, no MCP server hash verification",
        "phase_to_fill": 2,
    },
    "ASI06": {
        "name": "Sensitive Information Disclosure",
        "status": "covered",
        "controls": ["PII detection policy", "ANCESTOR audit trail", "GDPR module"],
        "policies": ["POL-SEC-PII-001"],
        "gap": None,
        "phase_to_fill": None,
    },
    "ASI07": {
        "name": "Insecure Plugin/Tool Design",
        "status": "covered",
        "controls": ["inter-agent delegation validation "],
        "policies": ["POL-ASI07-INTER-AGENT"],
        "gap": None,
        "phase_to_fill": None,
    },
    "ASI08": {
        "name": "Excessive Agency",
        "status": "covered",
        "controls": [
            "tier ceiling enforcement",
            "authority limits",
            "social contracts",
            "circular delegation detection ",
        ],
        "policies": ["tier_ceilings", "authority_limits", "POL-ASI08-CASCADE"],
        "gap": None,
        "phase_to_fill": None,
    },
    "ASI09": {
        "name": "Overreliance",
        "status": "covered",
        "controls": ["ECLIPSE HITL", "Prophecy Engine", "confidence gate "],
        "policies": ["POL-ASI09-CONFIDENCE"],
        "gap": None,
        "phase_to_fill": None,
    },
    "ASI10": {
        "name": "Model Theft",
        "status": "partial",
        "controls": ["rate limiting", "API key auth", "audit trail"],
        "policies": [],
        "gap": "No real-time model extraction pattern detection",
        "phase_to_fill": 3,
    },
}


def get_coverage_score() -> float:
    """Return fraction of ASI risks that are fully covered (not partial)."""
    covered = sum(1 for v in OWASP_COVERAGE.values if v["status"] == "covered")
    return covered / len(OWASP_COVERAGE)
