"""Benchmarks for the pure-Python policy engine rule evaluation loop.

These benchmarks isolate the CPU-bound work inside policy evaluation:
    - Rule matching (role/tier filter)
    - Amount threshold checks
    - Blocked/escalation action lookups
    - Aggregate verdict computation

No I/O, no DB, no HTTP — pure function performance.

Run:
    pytest benchmarks/test_policy_engine.py --benchmark-only -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_API = ROOT / "services" / "governance-api"
sys.path.insert(0, str(GOVERNANCE_API))


# ─────────────────────────────────────────────────────────────────────────────
# Stubs: replicate the policy structures used by governance.py
# These avoid DB round-trips so we can benchmark the pure logic.
# ─────────────────────────────────────────────────────────────────────────────

BLOCKED_ACTIONS = {
    "wire_transfer", "delete_account", "terminate_employee",
    "bypass_auth", "drop_table", "mass_email", "exfiltrate_data",
}

ESCALATION_ACTIONS = {
    "approve_payment", "approve_purchase", "modify_salary",
    "fire_employee", "access_pii", "bulk_delete",
}

TIER_CEILINGS = {
    "T0": 0.0,
    "T1": 1_000_000.0,
    "T2": 100_000.0,
    "T3": 10_000.0,
    "T4": 1_000.0,
}

SAMPLE_POLICIES = [
    {
        "policy_code": "POL-FIN-001",
        "applies_to_roles": ["*"],
        "applies_to_tiers": ["*"],
        "rule_definition": {"max_amount": 10_000, "blocked_actions": ["wire_transfer"]},
        "severity": "critical",
        "action_on_violation": "block",
    },
    {
        "policy_code": "POL-SEC-001",
        "applies_to_roles": ["analyst", "support"],
        "applies_to_tiers": ["T3", "T4"],
        "rule_definition": {"blocked_actions": ["access_pii"]},
        "severity": "high",
        "action_on_violation": "escalate",
    },
    {
        "policy_code": "POL-OPS-001",
        "applies_to_roles": ["*"],
        "applies_to_tiers": ["*"],
        "rule_definition": {"max_amount": 50_000},
        "severity": "medium",
        "action_on_violation": "escalate",
    },
    {
        "policy_code": "POL-GOV-001",
        "applies_to_roles": ["*"],
        "applies_to_tiers": ["T3", "T4"],
        "rule_definition": {"max_amount": 1_000},
        "severity": "low",
        "action_on_violation": "log",
    },
]


def _evaluate_policies_pure(
    agent_role: str,
    agent_tier: str,
    agent_trust_score: float,
    action_type: str,
    amount: float,
    policies: list[dict],
) -> dict:
    """
    Pure-Python policy evaluation — no I/O, no DB.

    This mirrors the core logic in governance.py:_evaluate_policy.
    Benchmarking this in isolation gives us the CPU cost of the rule loop.
    """
    violations = []
    escalations = []
    verdict = "APPROVED"
    risk = "LOW"

    # 1. Hard-block check (O(1) set lookup)
    if action_type in BLOCKED_ACTIONS:
        return {
            "verdict": "BLOCKED",
            "risk_score": "CRITICAL",
            "policy_matched": "HARD_BLOCK",
            "violations": [f"{action_type} is globally forbidden"],
            "requires_human_review": False,
        }

    # 2. Tier ceiling check (O(1))
    ceiling = TIER_CEILINGS.get(agent_tier, 0.0)
    if amount > ceiling:
        violations.append(f"Amount {amount} exceeds tier {agent_tier} ceiling {ceiling}")
        verdict = "BLOCKED"
        risk = "HIGH"

    # 3. Policy rule loop (O(P) where P = number of policies)
    for policy in policies:
        # Role filter
        if "*" not in policy["applies_to_roles"] and agent_role not in policy["applies_to_roles"]:
            continue
        # Tier filter
        if "*" not in policy["applies_to_tiers"] and agent_tier not in policy["applies_to_tiers"]:
            continue

        rule = policy["rule_definition"]

        # Max amount check
        if "max_amount" in rule and amount > rule["max_amount"]:
            violation_msg = (
                f"Policy {policy['policy_code']}: amount {amount} > max {rule['max_amount']}"
            )
            if policy["action_on_violation"] == "block":
                violations.append(violation_msg)
                verdict = "BLOCKED"
                risk = "HIGH"
            elif policy["action_on_violation"] == "escalate":
                escalations.append(violation_msg)
                if verdict == "APPROVED":
                    verdict = "ESCALATED"
                risk = "MEDIUM" if risk == "LOW" else risk

        # Blocked action check within policy
        if "blocked_actions" in rule and action_type in rule["blocked_actions"]:
            violation_msg = (
                f"Policy {policy['policy_code']}: action {action_type} is forbidden"
            )
            violations.append(violation_msg)
            verdict = "BLOCKED"
            risk = "CRITICAL"

    # 4. Escalation action check
    if action_type in ESCALATION_ACTIONS and verdict == "APPROVED":
        verdict = "ESCALATED"
        risk = "MEDIUM"

    # 5. Low-trust override
    if agent_trust_score < 0.3:
        verdict = "BLOCKED"
        risk = "HIGH" if risk == "LOW" else risk

    return {
        "verdict": verdict,
        "risk_score": risk,
        "violations": violations,
        "escalations": escalations,
        "requires_human_review": verdict == "ESCALATED",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Benchmarks
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicyEngineBenchmarks:
    """Pure-Python policy engine benchmarks — no I/O."""

    def test_bench_low_risk_single_policy(self, benchmark):
        """1 policy, low-risk action. Absolute minimum overhead."""
        result = benchmark.pedantic(
            _evaluate_policies_pure,
            args=("analyst", "T3", 0.8, "read_report", 0.0, SAMPLE_POLICIES[:1]),
            rounds=500,
            warmup_rounds=50,
        )
        assert result["verdict"] == "APPROVED"

    def test_bench_approved_4_policies(self, benchmark):
        """4 policies, approved action. Typical production workload."""
        result = benchmark.pedantic(
            _evaluate_policies_pure,
            args=("analyst", "T3", 0.8, "read_report", 100.0, SAMPLE_POLICIES),
            rounds=500,
            warmup_rounds=50,
        )
        assert result["verdict"] == "APPROVED"

    def test_bench_blocked_hard_block(self, benchmark):
        """Hard-block action — must short-circuit after first set lookup."""
        result = benchmark.pedantic(
            _evaluate_policies_pure,
            args=("analyst", "T3", 0.9, "wire_transfer", 100.0, SAMPLE_POLICIES),
            rounds=500,
            warmup_rounds=50,
        )
        assert result["verdict"] == "BLOCKED"

    def test_bench_tier_ceiling_violation(self, benchmark):
        """Amount exceeds tier ceiling — block after tier check."""
        result = benchmark.pedantic(
            _evaluate_policies_pure,
            args=("analyst", "T4", 0.9, "approve_payment", 50_000.0, SAMPLE_POLICIES),
            rounds=500,
            warmup_rounds=50,
        )
        assert result["verdict"] == "BLOCKED"

    def test_bench_policy_loop_100_policies(self, benchmark):
        """Stress: 100 policies in the loop. Measures O(P) scaling."""
        # Expand to 100 policies by repeating SAMPLE_POLICIES
        large_policy_set = (SAMPLE_POLICIES * 25)  # 100 total

        result = benchmark.pedantic(
            _evaluate_policies_pure,
            args=("analyst", "T3", 0.8, "read_report", 100.0, large_policy_set),
            rounds=100,
            warmup_rounds=10,
        )
        assert result["verdict"] in ("APPROVED", "ESCALATED", "BLOCKED")

    def test_bench_low_trust_agent(self, benchmark):
        """Low-trust agent (< 0.3) is blocked regardless of action."""
        result = benchmark.pedantic(
            _evaluate_policies_pure,
            args=("analyst", "T3", 0.1, "read_report", 0.0, SAMPLE_POLICIES),
            rounds=500,
            warmup_rounds=50,
        )
        assert result["verdict"] == "BLOCKED"


class TestPolicyEngineCorrectness:
    """Correctness assertions for the policy engine logic."""

    def test_hard_block_always_wins(self):
        """wire_transfer is always BLOCKED, regardless of trust or tier."""
        result = _evaluate_policies_pure("admin", "T1", 1.0, "wire_transfer", 0.0, [])
        assert result["verdict"] == "BLOCKED"
        assert result["risk_score"] == "CRITICAL"

    def test_approved_within_ceiling(self):
        """Action within tier ceiling and no policy violations → APPROVED."""
        result = _evaluate_policies_pure(
            "analyst", "T3", 0.9, "read_report", 500.0, SAMPLE_POLICIES
        )
        assert result["verdict"] == "APPROVED"

    def test_tier_t4_ceiling_1000(self):
        """T4 ceiling is 1000. Amount 1001 must be BLOCKED."""
        result = _evaluate_policies_pure(
            "analyst", "T4", 0.9, "purchase_item", 1001.0, []
        )
        assert result["verdict"] == "BLOCKED"

    def test_escalation_action_escalates(self):
        """approve_payment is in ESCALATION_ACTIONS → ESCALATED when no block."""
        result = _evaluate_policies_pure(
            "analyst", "T3", 0.8, "approve_payment", 50.0, []
        )
        assert result["verdict"] == "ESCALATED"
        assert result["requires_human_review"] is True

    def test_low_trust_overrides_approval(self):
        """Trust < 0.3 converts APPROVED to BLOCKED."""
        result = _evaluate_policies_pure(
            "analyst", "T3", 0.2, "read_report", 0.0, []
        )
        assert result["verdict"] == "BLOCKED"

    def test_empty_policy_set_basic_flow(self):
        """With no policies, only hard-blocks and tier ceilings apply."""
        # Normal action, no ceiling breach
        result = _evaluate_policies_pure("analyst", "T3", 0.8, "read_report", 100.0, [])
        assert result["verdict"] == "APPROVED"

    def test_policy_role_filter_excludes_irrelevant(self):
        """Policy with role=['manager'] should not affect role='analyst'."""
        manager_policy = [{
            "policy_code": "POL-MGR-001",
            "applies_to_roles": ["manager"],
            "applies_to_tiers": ["*"],
            "rule_definition": {"max_amount": 0},
            "severity": "high",
            "action_on_violation": "block",
        }]
        result = _evaluate_policies_pure("analyst", "T3", 0.9, "read_report", 100.0, manager_policy)
        assert result["verdict"] == "APPROVED", "Manager policy should not affect analyst"
