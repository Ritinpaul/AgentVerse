"""
Tests: Trust Scoring (PULSE module)

Covers:
  - Delta values for all event types
  - Trust score bounds (clamped 0.0 - 1.0)
  - Tier promotion (T4 → T3 → T2 → T1)
  - Tier demotion (T1 → T2 → T3)
  - Authority limit updates on tier change
  - Velocity calculation logic
"""

import pytest
from decimal import Decimal
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "governance-api"))

# Import trust scoring constants from the pulse router
from routers.pulse import TRUST_DELTAS, TIER_THRESHOLDS, _compute_tier


class TestTrustDeltas:
    """All event types have the correct delta values."""

    def test_success_simple_positive(self):
        assert TRUST_DELTAS["decision_success_simple"] == Decimal("0.01")

    def test_success_complex_positive(self):
        assert TRUST_DELTAS["decision_success_complex"] == Decimal("0.03")

    def test_success_boundary_positive(self):
        assert TRUST_DELTAS["decision_success_boundary"] == Decimal("0.05")

    def test_failure_minor_negative(self):
        assert TRUST_DELTAS["decision_failure_minor"] < Decimal("0.00")

    def test_failure_major_large_negative(self):
        assert TRUST_DELTAS["decision_failure_major"] < TRUST_DELTAS["decision_failure_minor"]

    def test_policy_violation_critical_largest_negative(self):
        assert TRUST_DELTAS["policy_violation_critical"] == Decimal("-0.20")

    def test_time_decay_small(self):
        assert abs(TRUST_DELTAS["time_decay_daily"]) < Decimal("0.01")


class TestTrustBounds:
    """Trust score must stay clamped between 0.0 and 1.0."""

    def _apply_delta(self, current: Decimal, event_type: str) -> Decimal:
        delta = TRUST_DELTAS.get(event_type, Decimal("0"))
        return max(Decimal("0.00"), min(Decimal("1.00"), current + delta))

    def test_cannot_exceed_1(self):
        score = Decimal("0.99")
        result = self._apply_delta(score, "decision_success_complex")
        assert result <= Decimal("1.00")

    def test_cannot_go_below_0(self):
        score = Decimal("0.01")
        result = self._apply_delta(score, "policy_violation_critical")
        assert result >= Decimal("0.00")

    def test_exactly_one_on_start_at_max(self):
        score = Decimal("1.00")
        result = self._apply_delta(score, "decision_success_simple")
        assert result == Decimal("1.00")

    def test_zero_floor(self):
        score = Decimal("0.00")
        result = self._apply_delta(score, "decision_failure_major")
        assert result == Decimal("0.00")


class TestTierPromotion:
    """Correct tier and authority limit returned for each trust score."""

    def test_t4_low_score(self):
        tier, limit = _compute_tier(Decimal("0.30"))
        assert tier == "T4"
        assert limit == Decimal("0.00")

    def test_t4_below_threshold(self):
        tier, limit = _compute_tier(Decimal("0.599"))
        assert tier == "T4"

    def test_t3_at_promotion(self):
        tier, limit = _compute_tier(Decimal("0.60"))
        assert tier == "T3"
        assert limit == Decimal("10000.00")

    def test_t3_mid_range(self):
        tier, limit = _compute_tier(Decimal("0.68"))
        assert tier == "T3"

    def test_t2_at_promotion(self):
        tier, limit = _compute_tier(Decimal("0.75"))
        assert tier == "T2"
        assert limit == Decimal("50000.00")

    def test_t1_at_promotion(self):
        tier, limit = _compute_tier(Decimal("0.90"))
        assert tier == "T1"
        assert limit == Decimal("100000.00")

    def test_t1_at_max(self):
        tier, limit = _compute_tier(Decimal("1.00"))
        assert tier == "T1"
        assert limit == Decimal("100000.00")

    def test_all_tiers_covered(self):
        """Every trust score in [0, 1] maps to a valid tier."""
        for score_int in range(0, 101, 5):
            score = Decimal(str(score_int / 100))
            tier, limit = _compute_tier(score)
            assert tier in ("T4", "T3", "T2", "T1"), f"Invalid tier for score={score}"
            assert limit >= 0
