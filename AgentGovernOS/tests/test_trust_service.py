"""
Tests: PULSE Trust Service

Covers:
  - Success events: correct type by complexity (simple/complex/boundary)
  - Confidence modifier: low confidence halves positive delta
  - Overconfidence penalty: high confidence + failure → major delta
  - Correct escalation: positive delta
  - Unnecessary escalation: negative delta
  - Human override: negative delta
  - Policy violations: dominate outcome (return only violation event)
  - Policy severity correctly maps to event type
  - Streak bonuses: 7d and 30d
  - No streak event on failure
  - Multiple events from single outcome (success + streak)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "crewai-engine"))

import pytest
from decimal import Decimal
from pulse.trust_service import TrustService, TaskOutcome, DecisionComplexity, OutcomeType


def make_outcome(**kwargs) -> TaskOutcome:
    defaults = {
        "agent_id": "agent-001",
        "task_id": "task-001",
        "decision_id": "dec-001",
        "complexity": DecisionComplexity.simple,
        "outcome": OutcomeType.success,
        "confidence_score": 0.85,
        "amount_involved": 10000.0,
        "streak_days": 0,
    }
    defaults.update(kwargs)
    return TaskOutcome(**defaults)


class TestSuccessEvents:
    ts = TrustService

    def test_simple_success_event_type(self):
        events = self.ts.evaluate(make_outcome(complexity=DecisionComplexity.simple))
        assert any(e.event_type == "decision_success_simple" for e in events)

    def test_complex_success_event_type(self):
        events = self.ts.evaluate(make_outcome(complexity=DecisionComplexity.complex))
        assert any(e.event_type == "decision_success_complex" for e in events)

    def test_boundary_success_event_type(self):
        events = self.ts.evaluate(make_outcome(complexity=DecisionComplexity.boundary))
        assert any(e.event_type == "decision_success_boundary" for e in events)

    def test_simple_delta_positive(self):
        events = self.ts.evaluate(make_outcome(complexity=DecisionComplexity.simple))
        main = next(e for e in events if "success" in e.event_type)
        assert main.delta > Decimal("0")

    def test_boundary_delta_larger_than_simple(self):
        simple = self.ts.evaluate(make_outcome(complexity=DecisionComplexity.simple))
        boundary = self.ts.evaluate(make_outcome(complexity=DecisionComplexity.boundary))
        s_delta = next(e.delta for e in simple if "success" in e.event_type)
        b_delta = next(e.delta for e in boundary if "success" in e.event_type)
        assert b_delta > s_delta

    def test_low_confidence_halves_delta(self):
        high_conf = self.ts.evaluate(make_outcome(confidence_score=0.90))
        low_conf = self.ts.evaluate(make_outcome(confidence_score=0.50))
        h_delta = next(e.delta for e in high_conf if "success" in e.event_type)
        l_delta = next(e.delta for e in low_conf if "success" in e.event_type)
        assert l_delta == h_delta * Decimal("0.50")


class TestFailureEvents:
    ts = TrustService

    def test_failure_event_type(self):
        events = self.ts.evaluate(make_outcome(outcome=OutcomeType.failure, confidence_score=0.60))
        assert any("failure" in e.event_type for e in events)

    def test_failure_delta_negative(self):
        events = self.ts.evaluate(make_outcome(outcome=OutcomeType.failure, confidence_score=0.60))
        main = next(e for e in events if "failure" in e.event_type)
        assert main.delta < Decimal("0")

    def test_overconfidence_failure_major_penalty(self):
        """High confidence + failure = major penalty (agent was adamant and wrong)."""
        events = self.ts.evaluate(make_outcome(outcome=OutcomeType.failure, confidence_score=0.90))
        main = next(e for e in events if "failure" in e.event_type)
        assert main.event_type == "decision_failure_major"

    def test_low_confidence_failure_minor_penalty(self):
        events = self.ts.evaluate(make_outcome(outcome=OutcomeType.failure, confidence_score=0.60))
        main = next(e for e in events if "failure" in e.event_type)
        assert main.event_type == "decision_failure_minor"


class TestEscalationEvents:
    ts = TrustService

    def test_correct_escalation_positive_delta(self):
        events = self.ts.evaluate(make_outcome(outcome=OutcomeType.escalated))
        main = next(e for e in events if e.event_type == "correct_escalation")
        assert main.delta > Decimal("0")

    def test_unnecessary_escalation_negative_delta(self):
        events = self.ts.evaluate(make_outcome(outcome=OutcomeType.unnecessary_escalation))
        main = next(e for e in events if e.event_type == "unnecessary_escalation")
        assert main.delta < Decimal("0")

    def test_human_override_negative_delta(self):
        events = self.ts.evaluate(make_outcome(outcome=OutcomeType.human_override))
        main = next(e for e in events if e.event_type == "human_override")
        assert main.delta < Decimal("0")


class TestPolicyViolations:
    ts = TrustService

    def test_violation_returns_only_violation_event(self):
        """Policy violation should dominate — no positive events generated."""
        events = self.ts.evaluate(make_outcome(
            outcome=OutcomeType.policy_violation,
            policy_violations=["POL-AUTH-LIMIT-001"],
            violation_severity="high",
        ))
        assert len(events) == 1
        assert "policy_violation" in events[0].event_type

    def test_critical_violation_largest_negative(self):
        events_crit = self.ts.evaluate(make_outcome(
            outcome=OutcomeType.policy_violation,
            policy_violations=["POL-001"],
            violation_severity="critical",
        ))
        events_low = self.ts.evaluate(make_outcome(
            outcome=OutcomeType.policy_violation,
            policy_violations=["POL-002"],
            violation_severity="low",
        ))
        assert events_crit[0].delta < events_low[0].delta

    def test_violation_severity_maps_correctly(self):
        for sev, expected_type in [
            ("low", "policy_violation_low"),
            ("high", "policy_violation_high"),
            ("critical", "policy_violation_critical"),
        ]:
            events = self.ts.evaluate(make_outcome(
                outcome=OutcomeType.policy_violation,
                policy_violations=["POL-X"],
                violation_severity=sev,
            ))
            assert events[0].event_type == expected_type


class TestStreakBonuses:
    ts = TrustService

    def test_7d_streak_bonus(self):
        events = self.ts.evaluate(make_outcome(streak_days=7))
        types = {e.event_type for e in events}
        assert "zero_incident_streak_7d" in types

    def test_30d_streak_bonus(self):
        events = self.ts.evaluate(make_outcome(streak_days=30))
        types = {e.event_type for e in events}
        assert "zero_incident_streak_30d" in types

    def test_no_streak_below_7d(self):
        events = self.ts.evaluate(make_outcome(streak_days=6))
        types = {e.event_type for e in events}
        assert "zero_incident_streak_7d" not in types
        assert "zero_incident_streak_30d" not in types

    def test_no_streak_on_failure(self):
        events = self.ts.evaluate(make_outcome(
            outcome=OutcomeType.failure, streak_days=30
        ))
        types = {e.event_type for e in events}
        assert "zero_incident_streak_30d" not in types

    def test_success_plus_streak_returns_two_events(self):
        events = self.ts.evaluate(make_outcome(streak_days=7))
        assert len(events) == 2

    def test_all_events_have_correct_agent_id(self):
        events = self.ts.evaluate(make_outcome(agent_id="agent-xyz", streak_days=7))
        assert all(e.agent_id == "agent-xyz" for e in events)
