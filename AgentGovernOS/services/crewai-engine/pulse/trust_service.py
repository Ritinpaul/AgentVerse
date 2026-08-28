"""
PULSE Trust Service — automates trust event generation from task outcomes.

Instead of manually recording trust events, the trust service evaluates
completed tasks and auto-generates appropriate trust events based on:

  1. Decision confidence score (how sure was the agent?)
  2. Decision complexity (simple vs complex vs boundary case)
  3. Outcome type (success, failure, escalation, override)
  4. Policy violations (if any occurred)
  5. Streak tracking (zero-incident streak bonuses)

This eliminates manual trust management — the system self-governs.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class DecisionComplexity(str, Enum):
    simple = "simple"         # Straightforward, clear-cut cases
    complex = "complex"       # Multi-factor analysis required
    boundary = "boundary"     # Edge cases near authority limits or policy thresholds


class OutcomeType(str, Enum):
    success = "success"
    failure = "failure"
    escalated = "escalated"         # Correct escalation (good thing)
    unnecessary_escalation = "unnecessary_escalation"
    human_override = "human_override"
    policy_violation = "policy_violation"


@dataclass
class TaskOutcome:
    """
    Structured outcome of a completed task — input to the trust engine.
    """
    agent_id: str
    task_id: str
    decision_id: str
    complexity: DecisionComplexity
    outcome: OutcomeType
    confidence_score: float          # 0.0 – 1.0, from the agent's output
    amount_involved: float = 0.0
    policy_violations: list = None   # List of violated policy codes
    violation_severity: str = "low"  # low / high / critical
    streak_days: int = 0             # Current zero-incident streak length

    def __post_init__(self):
        self.policy_violations = self.policy_violations or []


@dataclass
class TrustEvent:
    """A trust event to be recorded in the PULSE module."""
    agent_id: str
    event_type: str
    delta: Decimal
    reason: str
    trigger_decision_id: str
    metadata: dict


class TrustService:
    """
    Determines the correct trust event type and delta for a given task outcome.

    Algorithm:
      Step 1: Base event type from outcome + complexity
      Step 2: Confidence modifier (low confidence = reduced positive delta)
      Step 3: Policy violation override (violations dominate other factors)
      Step 4: Streak bonus (zero-incident streaks rewarded)
      Step 5: Generate TrustEvent(s) — may generate multiple events (e.g., success + streak)
    """

    # Base deltas — source of truth for all delta values
    BASE_DELTAS: dict[str, Decimal] = {
        "decision_success_simple":        Decimal("0.01"),
        "decision_success_complex":       Decimal("0.03"),
        "decision_success_boundary":      Decimal("0.05"),
        "correct_escalation":             Decimal("0.02"),
        "learning_milestone":             Decimal("0.02"),
        "zero_incident_streak_7d":        Decimal("0.03"),
        "zero_incident_streak_30d":       Decimal("0.05"),
        "decision_failure_minor":         Decimal("-0.05"),
        "decision_failure_major":         Decimal("-0.15"),
        "human_override":                 Decimal("-0.03"),
        "policy_violation_low":           Decimal("-0.05"),
        "policy_violation_high":          Decimal("-0.10"),
        "policy_violation_critical":      Decimal("-0.20"),
        "unnecessary_escalation":         Decimal("-0.01"),
        "time_decay_daily":               Decimal("-0.001"),
    }

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.85
    MEDIUM_CONFIDENCE = 0.70
    LOW_CONFIDENCE = 0.55  # Below this, successes still happen but delta is halved

    def evaluate(self, outcome: TaskOutcome) -> list[TrustEvent]:
        """
        Main entry point — evaluate a task outcome and return trust events.

        Returns a list because a single outcome can trigger multiple events
        (e.g., success event + streak bonus event).
        """
        events = []

        # ── Step 3: Policy violations dominate ──
        if outcome.outcome == OutcomeType.policy_violation and outcome.policy_violations:
            events.append(self._policy_violation_event(outcome))
            return events  # Don't add positive events when violations present

        # ── Step 1 + 2: Main outcome event ──
        main_event = self._main_event(outcome)
        if main_event:
            events.append(main_event)

        # ── Step 4: Streak bonuses ──
        streak_event = self._streak_event(outcome)
        if streak_event:
            events.append(streak_event)

        return events

    # ──────────────────────────────────────────────
    # Private event builders
    # ──────────────────────────────────────────────

    def _main_event(self, outcome: TaskOutcome) -> TrustEvent | None:
        """Generate the primary trust event based on outcome + complexity."""

        if outcome.outcome == OutcomeType.success:
            event_type = {
                DecisionComplexity.simple:   "decision_success_simple",
                DecisionComplexity.complex:  "decision_success_complex",
                DecisionComplexity.boundary: "decision_success_boundary",
            }[outcome.complexity]

            delta = self.BASE_DELTAS[event_type]

            # Confidence modifier: low confidence = halved delta
            if outcome.confidence_score < self.LOW_CONFIDENCE:
                delta = delta * Decimal("0.50")
                reason = (
                    f"Success ({outcome.complexity.value}) but low confidence "
                    f"({outcome.confidence_score:.2f}) — delta halved"
                )
            elif outcome.confidence_score >= self.HIGH_CONFIDENCE:
                reason = (
                    f"High-confidence {outcome.complexity.value} decision success "
                    f"(confidence={outcome.confidence_score:.2f})"
                )
            else:
                reason = (
                    f"{outcome.complexity.value.title} decision success "
                    f"(confidence={outcome.confidence_score:.2f})"
                )

        elif outcome.outcome == OutcomeType.failure:
            # Major failure if high-confidence but still failed (agent was adamant and wrong)
            if outcome.confidence_score >= self.HIGH_CONFIDENCE:
                event_type = "decision_failure_major"
                reason = (
                    f"Decision failed despite HIGH confidence ({outcome.confidence_score:.2f}) — "
                    "overconfidence penalty applied"
                )
            else:
                event_type = "decision_failure_minor"
                reason = (
                    f"Decision failed (confidence={outcome.confidence_score:.2f})"
                )
            delta = self.BASE_DELTAS[event_type]

        elif outcome.outcome == OutcomeType.escalated:
            event_type = "correct_escalation"
            delta = self.BASE_DELTAS[event_type]
            reason = f"Correctly escalated — agent recognized limits (amount=₹{outcome.amount_involved:,.0f})"

        elif outcome.outcome == OutcomeType.unnecessary_escalation:
            event_type = "unnecessary_escalation"
            delta = self.BASE_DELTAS[event_type]
            reason = "Unnecessary escalation — agent could have resolved within authority"

        elif outcome.outcome == OutcomeType.human_override:
            event_type = "human_override"
            delta = self.BASE_DELTAS[event_type]
            reason = "Human reviewer overrode agent decision"

        else:
            return None

        return TrustEvent(
            agent_id=outcome.agent_id,
            event_type=event_type,
            delta=delta,
            reason=reason,
            trigger_decision_id=outcome.decision_id,
            metadata={
                "confidence": outcome.confidence_score,
                "complexity": outcome.complexity.value,
                "amount": outcome.amount_involved,
            },
        )

    def _policy_violation_event(self, outcome: TaskOutcome) -> TrustEvent:
        """Create a trust event for a policy violation."""
        sev_map = {
            "low":      "policy_violation_low",
            "high":     "policy_violation_high",
            "critical": "policy_violation_critical",
        }
        event_type = sev_map.get(outcome.violation_severity, "policy_violation_low")
        delta = self.BASE_DELTAS[event_type]

        return TrustEvent(
            agent_id=outcome.agent_id,
            event_type=event_type,
            delta=delta,
            reason=(
                f"Policy violation ({outcome.violation_severity}): "
                f"{', '.join(outcome.policy_violations)}"
            ),
            trigger_decision_id=outcome.decision_id,
            metadata={
                "violated_policies": outcome.policy_violations,
                "severity": outcome.violation_severity,
            },
        )

    def _streak_event(self, outcome: TaskOutcome) -> TrustEvent | None:
        """Generate a streak bonus event if applicable."""
        if outcome.outcome not in (OutcomeType.success, OutcomeType.escalated):
            return None

        if outcome.streak_days >= 30:
            event_type = "zero_incident_streak_30d"
        elif outcome.streak_days >= 7:
            event_type = "zero_incident_streak_7d"
        else:
            return None

        return TrustEvent(
            agent_id=outcome.agent_id,
            event_type=event_type,
            delta=self.BASE_DELTAS[event_type],
            reason=f"Zero-incident streak bonus: {outcome.streak_days} days",
            trigger_decision_id=outcome.decision_id,
            metadata={"streak_days": outcome.streak_days},
        )
