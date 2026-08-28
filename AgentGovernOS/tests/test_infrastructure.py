"""
Tests: Environment Registry

Covers:
  - Heartbeat registers agent
  - Heartbeat updates last_seen
  - is_alive True within TTL
  - status "alive" / "stale" / "dead"
  - fleet_status shows correct counts
  - get_agents_in_environment filters correctly
  - Environment crossing alert (client → cloud)
  - Allowed crossing (cloud → edge) = no alert
  - get_environment_history tracks sequence

Tests: Local Policy Enforcer

Covers:
  - Empty rule set → allow
  - amount_limit pass / fail
  - trust_minimum pass / fail
  - tier_required pass / fail
  - tier_minimum pass / fail
  - action_allowed pass / fail
  - authority_limit pass / fail
  - Unknown rule type → allow (fail-open)
  - Multiple rules: first failure returns deny
  - rules_checked counter correct

Tests: Local Ledger

Covers:
  - record_decision returns an ID
  - get_unsynced returns all unsynced entries
  - mark_synced correctly flags entries
  - unsynced_count decreases after mark_synced
  - LocalDecision hash computed on creation
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "identity-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "edge-gateway"))

import time
import pytest
from environment_registry import EnvironmentRegistry
from identity.local_enforcer import LocalPolicyEnforcer
from identity.local_ledger import LocalLedger


# ──────────────────────────────────────────────
# Environment Registry
# ──────────────────────────────────────────────

class TestEnvironmentRegistry:
    def make_reg(self) -> EnvironmentRegistry:
        return EnvironmentRegistry

    def test_heartbeat_registers_agent(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "cloud", "vm-01")
        loc = reg.get_location("agent-001")
        assert loc is not None
        assert loc.agent_id == "agent-001"
        assert loc.environment == "cloud"

    def test_heartbeat_updates_last_seen(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "cloud", "vm-01")
        loc1 = reg.get_location("agent-001")
        time.sleep(0.01)
        reg.heartbeat("agent-001", "cloud", "vm-01")
        loc2 = reg.get_location("agent-001")
        assert loc2.last_seen >= loc1.last_seen

    def test_is_alive_fresh_heartbeat(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "edge", "edge-device-01")
        loc = reg.get_location("agent-001")
        assert loc.is_alive is True
        assert loc.status == "alive"

    def test_unknown_environment_returns_error(self):
        reg = self.make_reg
        result = reg.heartbeat("agent-001", "invalid-env", "host-01")
        assert result["status"] == "error"

    def test_fleet_status_contains_agents(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "cloud", "vm-01")
        reg.heartbeat("agent-002", "edge", "edge-01")
        status = reg.fleet_status
        assert status["total_agents"] == 2
        assert "cloud" in status["by_environment"]
        assert "edge" in status["by_environment"]

    def test_get_agents_in_environment(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "cloud", "vm-01")
        reg.heartbeat("agent-002", "cloud", "vm-02")
        reg.heartbeat("agent-003", "edge", "edge-01")
        cloud_agents = reg.get_agents_in_environment("cloud")
        assert len(cloud_agents) == 2

    def test_client_to_cloud_crossing_flagged(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "client", "laptop-01")
        result = reg.heartbeat("agent-001", "cloud", "vm-01")  # suspicious crossing
        assert result["status"] == "alert"
        assert result["alert"]["type"] == "unauthorized_environment_crossing"

    def test_cloud_to_edge_crossing_allowed(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "cloud", "vm-01")
        result = reg.heartbeat("agent-001", "edge", "edge-01")
        assert result["status"] == "ok"

    def test_environment_history_tracked(self):
        reg = self.make_reg
        reg.heartbeat("agent-001", "cloud", "vm-01")
        reg.heartbeat("agent-001", "edge", "edge-01")
        history = reg.get_environment_history("agent-001")
        assert history == ["cloud", "edge"]


# ──────────────────────────────────────────────
# Local Policy Enforcer
# ──────────────────────────────────────────────

class TestLocalPolicyEnforcer:
    def make_enforcer(self, rules=None) -> LocalPolicyEnforcer:
        e = LocalPolicyEnforcer
        if rules:
            e.load_policy_bundle(rules, version="test-1")
        return e

    def test_no_rules_allows(self):
        e = self.make_enforcer
        verdict = e.evaluate("T2", 0.75, 50000, "execute", 1000)
        assert verdict.verdict == "allow"

    def test_amount_limit_pass(self):
        e = self.make_enforcer([{"type": "amount_limit", "max_amount": 50000}])
        verdict = e.evaluate("T2", 0.75, 50000, "execute", 50000)
        assert verdict.verdict == "allow"

    def test_amount_limit_fail(self):
        e = self.make_enforcer([{"type": "amount_limit", "max_amount": 50000, "on_fail": "deny"}])
        verdict = e.evaluate("T2", 0.75, 50000, "execute", 50001)
        assert verdict.verdict == "deny"

    def test_trust_minimum_pass(self):
        e = self.make_enforcer([{"type": "trust_minimum", "min_trust": 0.70}])
        verdict = e.evaluate("T2", 0.75, 50000, "execute", 0)
        assert verdict.verdict == "allow"

    def test_trust_minimum_fail(self):
        e = self.make_enforcer([{"type": "trust_minimum", "min_trust": 0.70, "on_fail": "deny"}])
        verdict = e.evaluate("T4", 0.50, 0, "execute", 0)
        assert verdict.verdict == "deny"

    def test_tier_required_pass(self):
        e = self.make_enforcer([{"type": "tier_required", "allowed_tiers": ["T1", "T2"]}])
        verdict = e.evaluate("T1", 0.90, 100000, "execute", 0)
        assert verdict.verdict == "allow"

    def test_tier_required_fail(self):
        e = self.make_enforcer([{"type": "tier_required", "allowed_tiers": ["T1"], "on_fail": "deny"}])
        verdict = e.evaluate("T3", 0.65, 10000, "execute", 0)
        assert verdict.verdict == "deny"

    def test_tier_minimum_pass(self):
        e = self.make_enforcer([{"type": "tier_minimum", "min_tier": "T2"}])
        verdict = e.evaluate("T1", 0.90, 100000, "execute", 0)  # T1 > T2 in rank
        assert verdict.verdict == "allow"

    def test_tier_minimum_fail(self):
        e = self.make_enforcer([{"type": "tier_minimum", "min_tier": "T2", "on_fail": "deny"}])
        verdict = e.evaluate("T4", 0.55, 0, "execute", 0)
        assert verdict.verdict == "deny"

    def test_action_allowed_pass(self):
        e = self.make_enforcer([{"type": "action_allowed", "allowed_actions": ["read", "execute"]}])
        verdict = e.evaluate("T2", 0.75, 50000, "execute", 0)
        assert verdict.verdict == "allow"

    def test_action_allowed_fail(self):
        e = self.make_enforcer([{"type": "action_allowed", "allowed_actions": ["read"], "on_fail": "deny"}])
        verdict = e.evaluate("T2", 0.75, 50000, "write", 0)
        assert verdict.verdict == "deny"

    def test_unknown_rule_type_allows(self):
        e = self.make_enforcer([{"type": "quantum_rule_doesnt_exist"}])
        verdict = e.evaluate("T2", 0.75, 50000, "execute", 0)
        assert verdict.verdict == "allow"

    def test_rules_checked_count(self):
        rules = [
            {"type": "trust_minimum", "min_trust": 0.60},
            {"type": "tier_minimum", "min_tier": "T3"},
        ]
        e = self.make_enforcer(rules)
        verdict = e.evaluate("T2", 0.75, 10000, "execute", 0)
        assert verdict.rules_checked == 2

    def test_first_failing_rule_short_circuits(self):
        rules = [
            {"type": "amount_limit", "max_amount": 100, "on_fail": "deny"},
            {"type": "trust_minimum", "min_trust": 0.99, "on_fail": "escalate"},
        ]
        e = self.make_enforcer(rules)
        verdict = e.evaluate("T1", 0.40, 100000, "execute", 200)
        # First rule fails → deny, never reaches second rule
        assert verdict.verdict == "deny"
        assert verdict.rules_checked == 1


# ──────────────────────────────────────────────
# Local Ledger
# ──────────────────────────────────────────────

class TestLocalLedger:
    def make_ledger(self) -> LocalLedger:
        return LocalLedger(gateway_id="test-gateway")

    def test_record_returns_id(self):
        ledger = self.make_ledger
        decision_id = ledger.record_decision("a1", "execute", "db", 0, "edge", "allow", "ok", "jti-1")
        assert isinstance(decision_id, str) and len(decision_id) > 10

    def test_get_unsynced_returns_all_initially(self):
        ledger = self.make_ledger
        ledger.record_decision("a1", "execute", "db", 0, "edge", "allow", "ok", "jti-1")
        ledger.record_decision("a2", "write", "table", 1000, "edge", "deny", "limit", "jti-2")
        assert ledger.unsynced_count == 2

    def test_mark_synced_decreases_unsynced(self):
        ledger = self.make_ledger
        id1 = ledger.record_decision("a1", "execute", "db", 0, "edge", "allow", "ok", "jti-1")
        id2 = ledger.record_decision("a2", "write", "table", 0, "edge", "allow", "ok", "jti-2")
        ledger.mark_synced([id1])
        assert ledger.unsynced_count == 1

    def test_mark_synced_returns_count(self):
        ledger = self.make_ledger
        ids = [ledger.record_decision("a1", "x", "r", 0, "edge", "allow", "ok", "j") for _ in range(3)]
        count = ledger.mark_synced(ids[:2])
        assert count == 2

    def test_ledger_size(self):
        ledger = self.make_ledger
        for i in range(5):
            ledger.record_decision(f"a{i}", "execute", "db", 0, "edge", "allow", "ok", "jti")
        assert ledger.size == 5

    def test_local_decision_has_hash(self):
        ledger = self.make_ledger
        ledger.record_decision("a1", "execute", "db", 0, "edge", "allow", "ok", "jti-1")
        entries = ledger.get_unsynced
        assert len(entries[0].hash) == 64
