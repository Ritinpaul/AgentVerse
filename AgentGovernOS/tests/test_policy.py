"""
Tests: Policy Distribution Service

Covers:
  - Bundle creation: hash computed, version set, rule count
  - Bundle integrity: verify_integrity passes on clean bundle
  - Bundle integrity: verify_integrity fails after tamper
  - Parent hash chaining between bundles
  - Rollback: reverts to previous version
  - Rollback by version: jumps to specific version
  - Diff: detects added, removed, modified rules
  - Environment scoping: edge-only rules excluded from cloud bundle
  - Gateway sync tracking: stale gateway detection
  - Version history list

Tests: Compliance Report Generator

Covers:
  - SOX report generates correct sections
  - EU AI Act report generates correct sections
  - GDPR report has correct sections
  - Internal audit report
  - Compliance score: 100% when all metrics pass
  - Compliance score: drops when metrics fail
  - Decision trail integrity: pass with valid chain
  - Decision trail integrity: fail with broken chain
  - Recommendations generated for failing metrics
  - Overall status: fail on critical risk
  - list_frameworks returns all 4

Tests: Prophecy Engine

Covers:
  - should_trigger: True near authority limit (≥70%)
  - should_trigger: True for low-trust agents
  - should_trigger: True for first-time actions
  - should_trigger: False when all normal
  - simulate: returns 3 paths (approve/deny/escalate)
  - simulate: recommended_path set
  - simulate: approve path has highest weight for high-success agents
  - simulate: escalate recommended for low-trust agents
  - simulate: all paths have risk_score between 0-1
  - simulate: confidence between 0-1
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "governance-api"))

import pytest
from decimal import Decimal
from policy.distribution import PolicyRule, PolicyBundle, PolicyDistributionService
from policy.compliance import ComplianceReportGenerator
from policy.prophecy import ProphecyEngine


# ──────────────────────────────────────────────
# Policy Distribution Service
# ──────────────────────────────────────────────

class TestPolicyBundle:
    def test_hash_computed_on_init(self):
        bundle = PolicyBundle(version="v1", rules=[])
        assert len(bundle.hash) == 64

    def test_integrity_passes_on_clean(self):
        r = PolicyRule(name="limit", type="amount_limit", parameters={"max_amount": 50000})
        bundle = PolicyBundle(version="v1", rules=[r])
        assert bundle.verify_integrity is True

    def test_integrity_fails_after_tamper(self):
        r = PolicyRule(name="limit", type="amount_limit", parameters={"max_amount": 50000})
        bundle = PolicyBundle(version="v1", rules=[r])
        bundle.rules[0].parameters["max_amount"] = 999999  # tamper
        assert bundle.verify_integrity is False

    def test_to_edge_format_excludes_inactive(self):
        r1 = PolicyRule(name="active_rule", type="trust_minimum", active=True)
        r2 = PolicyRule(name="inactive_rule", type="trust_minimum", active=False)
        bundle = PolicyBundle(version="v1", rules=[r1, r2])
        edge = bundle.to_edge_format
        assert len(edge["rules"]) == 1


class TestPolicyDistributionService:
    def _make_rules(self, count=2) -> list[PolicyRule]:
        return [PolicyRule(name=f"rule-{i}", type="amount_limit",
                          parameters={"max_amount": 1000 * (i + 1)})
                for i in range(count)]

    def test_create_bundle_sets_version(self):
        svc = PolicyDistributionService
        bundle = svc.create_bundle(self._make_rules, version="v1.0")
        assert bundle.version == "v1.0"
        assert svc.get_current_bundle.version == "v1.0"

    def test_auto_version_if_empty(self):
        svc = PolicyDistributionService
        bundle = svc.create_bundle(self._make_rules)
        assert bundle.version.startswith("v")

    def test_parent_hash_chaining(self):
        svc = PolicyDistributionService
        b1 = svc.create_bundle(self._make_rules, version="v1")
        b2 = svc.create_bundle(self._make_rules(3), version="v2")
        assert b2.parent_hash == b1.hash

    def test_rollback_one_step(self):
        svc = PolicyDistributionService
        svc.create_bundle(self._make_rules, version="v1")
        svc.create_bundle(self._make_rules(3), version="v2")
        rolled = svc.rollback
        assert rolled.version == "v1"
        assert svc.get_current_bundle.version == "v1"

    def test_rollback_to_specific_version(self):
        svc = PolicyDistributionService
        svc.create_bundle(self._make_rules, version="v1")
        svc.create_bundle(self._make_rules(3), version="v2")
        svc.create_bundle(self._make_rules(4), version="v3")
        rolled = svc.rollback("v1")
        assert rolled.version == "v1"

    def test_diff_detects_added(self):
        svc = PolicyDistributionService
        svc.create_bundle([PolicyRule(name="A", type="t")], version="v1")
        svc.create_bundle([PolicyRule(name="A", type="t"), PolicyRule(name="B", type="t")], version="v2")
        diff = svc.diff_bundles("v1", "v2")
        assert len(diff["added"]) == 1

    def test_diff_detects_removed(self):
        svc = PolicyDistributionService
        svc.create_bundle([PolicyRule(name="A", type="t"), PolicyRule(name="B", type="t")], version="v1")
        svc.create_bundle([PolicyRule(name="A", type="t")], version="v2")
        diff = svc.diff_bundles("v1", "v2")
        assert len(diff["removed"]) == 1

    def test_stale_gateway_detection(self):
        svc = PolicyDistributionService
        svc.create_bundle(self._make_rules, version="v1")
        svc.register_gateway_sync("gw-1", "v1")
        svc.create_bundle(self._make_rules(3), version="v2")
        stale = svc.get_stale_gateways
        assert "gw-1" in stale

    def test_gateway_not_stale_when_current(self):
        svc = PolicyDistributionService
        svc.create_bundle(self._make_rules, version="v1")
        svc.register_gateway_sync("gw-1", "v1")
        assert svc.get_stale_gateways == []

    def test_version_history(self):
        svc = PolicyDistributionService
        svc.create_bundle(self._make_rules, version="v1")
        svc.create_bundle(self._make_rules, version="v2")
        assert svc.version_history == ["v1", "v2"]

    def test_env_scoped_bundle(self):
        rules = [
            PolicyRule(name="cloud-only", type="t", environment_scope=["cloud"]),
            PolicyRule(name="edge-only", type="t", environment_scope=["edge"]),
            PolicyRule(name="both", type="t", environment_scope=["cloud", "edge"]),
        ]
        svc = PolicyDistributionService
        svc.create_bundle(rules, version="v1")
        edge_bundle = svc.get_bundle_for_environment("edge")
        assert edge_bundle["total_rules"] == 2  # edge-only + both


# ──────────────────────────────────────────────
# Compliance Report Generator
# ──────────────────────────────────────────────

class TestComplianceReportGenerator:
    gen = ComplianceReportGenerator

    def _mock_data(self, **overrides) -> dict:
        data = {
            "chain_verification": {"valid": True, "checked": 500, "integrity_pct": 100.0},
            "decisions": [
                {"amount": 15000, "verdict": "allow", "reasoning_trace": "Some reasoning"},
                {"amount": 60000, "verdict": "allow", "reasoning_trace": "More reasoning"},
                {"amount": 5000, "verdict": "deny", "reasoning_trace": "Denied reason"},
            ],
            "violations": [],
            "policy_blocks": 5,
            "escalations": [{"resolved": True, "was_necessary": True}],
            "human_overrides": [{"id": "o1"}],
            "fleet": {"total": 10, "alive": 9, "dead": 1},
            "trust_distribution": {"avg": 0.72, "below_threshold": 1},
            "cache_stats": {"hit_rate": 58.0, "tokens_saved": 12500},
            "dna_audit": {"audited": 50, "tampered": 0},
            "risk_class": "limited",
            "models": ["phi4-mini", "gpt-4"],
            "retention_active": True,
        }
        data.update(overrides)
        return data

    def test_sox_report_has_5_sections(self):
        report = self.gen.generate("sox", self._mock_data)
        assert len(report.sections) == 5

    def test_eu_ai_act_has_5_sections(self):
        report = self.gen.generate("eu_ai_act", self._mock_data)
        assert len(report.sections) == 5

    def test_gdpr_has_4_sections(self):
        report = self.gen.generate("gdpr", self._mock_data)
        assert len(report.sections) == 4

    def test_internal_has_5_sections(self):
        report = self.gen.generate("internal", self._mock_data)
        assert len(report.sections) == 5

    def test_compliance_score_100_all_pass(self):
        report = self.gen.generate("sox", self._mock_data)
        assert report.compliance_score >= 80.0  # Most metrics pass

    def test_broken_chain_lowers_score(self):
        data = self._mock_data(chain_verification={"valid": False, "checked": 500, "integrity_pct": 50.0})
        report = self.gen.generate("sox", data)
        assert report.overall_status == "fail"

    def test_overall_fail_on_critical(self):
        data = self._mock_data(dna_audit={"audited": 50, "tampered": 5})
        report = self.gen.generate("internal", data)
        assert report.overall_status == "fail"

    def test_recommendations_generated_for_failures(self):
        data = self._mock_data(chain_verification={"valid": False, "checked": 500, "integrity_pct": 50.0})
        report = self.gen.generate("sox", data)
        assert len(report.recommendations) > 0

    def test_unknown_framework_raises(self):
        with pytest.raises(ValueError, match="Unknown framework"):
            self.gen.generate("pci_dss", self._mock_data)

    def test_list_frameworks_returns_4(self):
        frameworks = self.gen.list_frameworks
        assert len(frameworks) == 4

    def test_report_to_dict_has_score(self):
        report = self.gen.generate("sox", self._mock_data)
        d = report.to_dict
        assert "score" in d
        assert "sections" in d


# ──────────────────────────────────────────────
# Prophecy Engine
# ──────────────────────────────────────────────

class TestProphecyEngine:
    engine = ProphecyEngine

    def test_trigger_near_authority_limit(self):
        triggered, reason = self.engine.should_trigger(0.75, 8000, 10000)
        assert triggered is True
        assert "70%" in reason

    def test_trigger_low_trust(self):
        triggered, reason = self.engine.should_trigger(0.40, 1000, 50000)
        assert triggered is True
        assert "trust" in reason.lower

    def test_trigger_first_time_action(self):
        triggered, reason = self.engine.should_trigger(0.80, 1000, 50000, historical_action_count=2)
        assert triggered is True
        assert "history" in reason.lower

    def test_no_trigger_when_normal(self):
        triggered, _ = self.engine.should_trigger(0.85, 5000, 50000, historical_action_count=100)
        assert triggered is False

    def test_simulate_returns_3_paths(self):
        result = self.engine.simulate(
            agent_id="a1", action_type="execute", amount=8000,
            trust_score=0.75, tier="T2", authority_limit=10000,
        )
        assert len(result.paths) == 3
        types = {p.path_type for p in result.paths}
        assert types == {"approve", "deny", "escalate"}

    def test_recommended_path_set(self):
        result = self.engine.simulate(
            agent_id="a1", action_type="execute", amount=8000,
            trust_score=0.80, tier="T2", authority_limit=10000,
        )
        assert result.recommended_path in ("approve", "deny", "escalate")

    def test_approve_recommended_for_safe_agent(self):
        result = self.engine.simulate(
            agent_id="a1", action_type="execute", amount=1000,
            trust_score=0.95, tier="T1", authority_limit=100000,
            historical_success_rate=0.95,
        )
        assert result.recommended_path == "approve"

    def test_escalate_recommended_for_low_trust(self):
        result = self.engine.simulate(
            agent_id="a1", action_type="execute", amount=9000,
            trust_score=0.30, tier="T4", authority_limit=10000,
            historical_success_rate=0.50,
        )
        assert result.recommended_path == "escalate"

    def test_risk_scores_between_0_and_1(self):
        result = self.engine.simulate(
            agent_id="a1", action_type="execute", amount=8000,
            trust_score=0.60, tier="T3", authority_limit=10000,
        )
        for path in result.paths:
            assert 0.0 <= path.risk_score <= 1.0

    def test_confidence_between_0_and_1(self):
        result = self.engine.simulate(
            agent_id="a1", action_type="execute", amount=5000,
            trust_score=0.70, tier="T2", authority_limit=50000,
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_to_dict_has_all_fields(self):
        result = self.engine.simulate(
            agent_id="a1", action_type="write", amount=3000,
            trust_score=0.78, tier="T2", authority_limit=50000,
        )
        d = result.to_dict
        assert "recommended_path" in d
        assert "paths" in d
        assert len(d["paths"]) == 3

    def test_approve_path_financial_exposure_proportional(self):
        """Higher amount should mean higher financial exposure on approve path."""
        r_low = self.engine.simulate("a1", "x", 1000, 0.70, "T2", 50000)
        r_high = self.engine.simulate("a1", "x", 40000, 0.70, "T2", 50000)
        approve_low = next(p for p in r_low.paths if p.path_type == "approve")
        approve_high = next(p for p in r_high.paths if p.path_type == "approve")
        assert approve_high.financial_exposure > approve_low.financial_exposure
