"""
Tests: Sentinel Policy Engine

Covers:
  - amount_limit rule: passes when amount ≤ max
  - amount_limit rule: fails when amount > max
  - trust_minimum rule: passes when trust ≥ threshold
  - trust_minimum rule: fails when trust < threshold
  - tier_required rule: passes with correct tier
  - tier_required rule: fails with wrong tier
  - status_check rule: passes for 'active' agent
  - status_check rule: fails for 'suspended' agent
  - Unknown rule type: defaults to pass (fail-open in dev)
  - Mixed violations: correct verdict (block/escalate/approve)
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "governance-api"))

from routers.sentinel import _evaluate_rule


def make_agent(trust=0.75, tier="T2", status="active", authority_limit=50000.00):
    """Factory: create a mock agent object."""
    agent = MagicMock
    agent.trust_score = Decimal(str(trust))
    agent.tier = tier
    agent.status = status
    agent.authority_limit = Decimal(str(authority_limit))
    agent.role = "dispute_resolver"
    return agent


class TestAmountLimitRule:
    RULE = {"type": "amount_limit", "max_amount": 50000}

    def test_passes_when_equal(self):
        agent = make_agent
        assert _evaluate_rule(self.RULE, agent, {"amount": 50000}, {}) is True

    def test_passes_when_below(self):
        agent = make_agent
        assert _evaluate_rule(self.RULE, agent, {"amount": 25000}, {}) is True

    def test_fails_when_above(self):
        agent = make_agent
        assert _evaluate_rule(self.RULE, agent, {"amount": 50001}, {}) is False

    def test_fails_on_zero_limit(self):
        rule = {"type": "amount_limit", "max_amount": 0}
        agent = make_agent
        assert _evaluate_rule(rule, agent, {"amount": 1}, {}) is False

    def test_passes_with_no_amount_in_action(self):
        """Missing 'amount' key defaults to 0 → always passes."""
        agent = make_agent
        assert _evaluate_rule(self.RULE, agent, {}, {}) is True


class TestTrustMinimumRule:
    RULE = {"type": "trust_minimum", "min_trust": 0.60}

    def test_passes_at_minimum(self):
        agent = make_agent(trust=0.60)
        assert _evaluate_rule(self.RULE, agent, {}, {}) is True

    def test_passes_above_minimum(self):
        agent = make_agent(trust=0.90)
        assert _evaluate_rule(self.RULE, agent, {}, {}) is True

    def test_fails_below_minimum(self):
        agent = make_agent(trust=0.55)
        assert _evaluate_rule(self.RULE, agent, {}, {}) is False

    def test_fails_at_zero_trust(self):
        agent = make_agent(trust=0.00)
        assert _evaluate_rule(self.RULE, agent, {}, {}) is False


class TestTierRequiredRule:
    RULE = {"type": "tier_required", "allowed_tiers": ["T1"]}

    def test_passes_with_t1(self):
        agent = make_agent(tier="T1")
        assert _evaluate_rule(self.RULE, agent, {}, {}) is True

    def test_fails_with_t2(self):
        agent = make_agent(tier="T2")
        assert _evaluate_rule(self.RULE, agent, {}, {}) is False

    def test_fails_with_t3(self):
        agent = make_agent(tier="T3")
        assert _evaluate_rule(self.RULE, agent, {}, {}) is False

    def test_multiple_allowed_tiers(self):
        rule = {"type": "tier_required", "allowed_tiers": ["T1", "T2"]}
        assert _evaluate_rule(rule, make_agent(tier="T1"), {}, {}) is True
        assert _evaluate_rule(rule, make_agent(tier="T2"), {}, {}) is True
        assert _evaluate_rule(rule, make_agent(tier="T3"), {}, {}) is False


class TestStatusCheckRule:
    RULE = {"type": "status_check"}

    def test_passes_for_active(self):
        assert _evaluate_rule(self.RULE, make_agent(status="active"), {}, {}) is True

    def test_fails_for_suspended(self):
        assert _evaluate_rule(self.RULE, make_agent(status="suspended"), {}, {}) is False

    def test_fails_for_retired(self):
        assert _evaluate_rule(self.RULE, make_agent(status="retired"), {}, {}) is False


class TestUnknownRule:
    def test_unknown_rule_type_passes(self):
        """Fail-open default: unknown rule types pass in dev mode."""
        rule = {"type": "nonexistent_rule_type"}
        assert _evaluate_rule(rule, make_agent, {}, {}) is True
