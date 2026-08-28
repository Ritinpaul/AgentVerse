"""
Local Policy Enforcer — edge-side rule evaluation without control plane calls.

Enforces a downloaded subset of the full SENTINEL policy set locally.
Runs 100% offline on the last-known policy bundle.

Policy evaluation is intentionally lightweight at the edge:
  - No external calls
  - Sub-millisecond evaluation
  - Simple rule types: amount_limit, trust_minimum, tier_required, action_allowed
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

TIER_RANK = {"T1": 4, "T2": 3, "T3": 2, "T4": 1}


@dataclass
class EnforcerVerdict:
    verdict: str    # "allow" | "deny" | "escalate"
    reason: str
    rules_checked: int = 0


class LocalPolicyEnforcer:
    """
    Evaluates pre-downloaded policy rules locally without calling control plane.
    Policy bundles are pushed from SENTINEL via the sync client every 30 seconds.
    """

    def __init__(self):
        self._rules: list[dict] = []
        self._policy_version: str = "0"

    def load_policy_bundle(self, rules: list[dict], version: str) -> None:
        """Replace current rules with a new policy bundle from control plane."""
        self._rules = rules
        self._policy_version = version
        logger.info(f"[ENFORCER] Loaded {len(rules)} rules (version {version})")

    def evaluate(
        self,
        agent_tier: str,
        trust_score: float,
        authority_limit: float,
        action_type: str,
        amount: float = 0.0,
        context: dict = None,
    ) -> EnforcerVerdict:
        """
        Evaluate all rules against the given action.
        Returns the first failing rule's verdict, or 'allow' if all pass.
        """
        ctx = context or {}
        checked = 0

        for rule in self._rules:
            checked += 1
            passed = self._evaluate_rule(rule, agent_tier, trust_score, authority_limit,
                                         action_type, amount, ctx)
            if not passed:
                return EnforcerVerdict(
                    verdict=rule.get("on_fail", "deny"),
                    reason=f"Rule '{rule.get('name', rule.get('type'))}' failed",
                    rules_checked=checked,
                )

        return EnforcerVerdict(
            verdict="allow",
            reason="All local policies passed",
            rules_checked=checked,
        )

    def _evaluate_rule(self, rule: dict, tier: str, trust: float,
                       limit: float, action: str, amount: float, ctx: dict) -> bool:
        rule_type = rule.get("type", "")

        if rule_type == "amount_limit":
            max_amount = rule.get("max_amount", 0)
            return amount <= max_amount

        elif rule_type == "trust_minimum":
            return trust >= rule.get("min_trust", 0.0)

        elif rule_type == "tier_required":
            allowed = rule.get("allowed_tiers", [])
            return tier in allowed

        elif rule_type == "tier_minimum":
            min_tier = rule.get("min_tier", "T4")
            return TIER_RANK.get(tier, 0) >= TIER_RANK.get(min_tier, 0)

        elif rule_type == "action_allowed":
            return action in rule.get("allowed_actions", [])

        elif rule_type == "authority_limit":
            return amount <= limit

        # Unknown rule type: fail-open (permissive) at edge
        return True

    @property
    def policy_count(self) -> int:
        return len(self._rules)

    @property
    def policy_version(self) -> str:
        return self._policy_version
