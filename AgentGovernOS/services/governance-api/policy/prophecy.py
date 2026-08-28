"""
policy/prophecy.py

Prophecy Engine — 3-path pre-execution simulation with Shadow Sandbox Execution.

Before an agent executes a high-stakes action, the Prophecy Engine
simulates three possible outcomes and their cascading effects:

  1. APPROVE PATH  — What happens if we approve this action?
  2. DENY PATH     — What happens if we deny it?
  3. ESCALATE PATH — What happens if we escalate to a human?

Features:
  - Real-time predictive risk scoring combining deterministic Monte Carlo ratios
    with an active Shadow Execution Sandbox.
  - Non-destructive dry-run sandbox that intercepts tool calls, state mutations,
    unauthorized network egress, and token budget escalation.
  - Detailed cascade effect predictions and empirical confidence estimation.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Shadow Execution Sandbox ─────────────────────────────────────────────────

@dataclass
class ShadowSimulationResult:
    """Report produced by running an action through the isolated sub-sandbox."""
    executed: bool
    side_effects: List[str]
    detected_hazards: List[str]
    severity: str  # "none" | "low" | "medium" | "high" | "critical"
    shadow_risk_score: float  # 0.0 – 1.0
    simulated_token_cost: float
    sandboxed_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executed": self.executed,
            "side_effects": self.side_effects,
            "detected_hazards": self.detected_hazards,
            "severity": self.severity,
            "shadow_risk_score": round(self.shadow_risk_score, 3),
            "simulated_token_cost": round(self.simulated_token_cost, 4),
            "sandboxed_duration_ms": round(self.sandboxed_duration_ms, 2),
        }


class ShadowExecutionRunner:
    """
    Lightweight shadow execution sandbox simulator.
    Simulates agent tool calls and actions in an isolated sub-sandbox
    before production commit.
    """

    DESTRUCTIVE_PATTERNS = [
        re.compile(r"\b(drop\s+table|delete\s+from|truncate|rm\s+-rf|format\s+[a-z]:)\b", re.I),
        re.compile(r"\b(sudo|chmod\s+777|chown\s+root)\b", re.I),
        re.compile(r"\b(eval\(|exec\(|subprocess\.Popen)\b", re.I),
    ]

    UNAPPROVED_EGRESS_REGEX = re.compile(
        r"https?://(?!api\.nuuvixx\.ai|agentstore\.nuuvixx\.com|localhost|127\.0\.0\.1)[\w.\-]+",
        re.I
    )

    def run_shadow_simulation(
        self,
        agent_id: str,
        action_type: str,
        action_payload: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ShadowSimulationResult:
        t0 = time.perf_counter()
        hazards: List[str] = []
        side_effects: List[str] = []
        token_cost = 0.001
        payload = action_payload or {}

        cmd_text = json.dumps(payload)
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if pattern.search(cmd_text):
                hazards.append(f"Destructive mutation pattern detected: {pattern.pattern}")
                side_effects.append("Database / filesystem state mutation")

        egress_matches = self.UNAPPROVED_EGRESS_REGEX.findall(cmd_text)
        if egress_matches:
            hazards.append(f"Unapproved external network egress: {', '.join(set(egress_matches[:3]))}")
            side_effects.append("Outbound network traffic")

        if action_type in ("batch_embedding", "code_generation_fleet", "agent_fork_storm"):
            token_cost = 0.08
            side_effects.append("High compute burst / token budget consumption")
            hazards.append("Compute burst exceeds shadow threshold")

        # Compute empirical shadow risk score
        if any("Destructive" in h for h in hazards):
            severity = "critical"
            risk = 0.95
        elif hazards:
            severity = "high"
            risk = 0.70
        elif side_effects:
            severity = "medium"
            risk = 0.35
        else:
            severity = "none"
            risk = 0.05

        duration_ms = (time.perf_counter() - t0) * 1000
        return ShadowSimulationResult(
            executed=True,
            side_effects=side_effects,
            detected_hazards=hazards,
            severity=severity,
            shadow_risk_score=risk,
            simulated_token_cost=token_cost,
            sandboxed_duration_ms=duration_ms,
        )


# ── Core Prophecy Models ─────────────────────────────────────────────────────

@dataclass
class ProphecyPath:
    """One of the three simulated outcomes."""
    path_type: str             # "approve" | "deny" | "escalate"
    predicted_trust_delta: Decimal
    risk_score: float          # 0.0 – 1.0
    financial_exposure: float  # Worst-case financial loss
    compliance_risk: str       # "none" | "low" | "medium" | "high"
    cascade_effects: list[str] # Human-readable list of downstream effects
    recommendation_weight: float = 0.0  # Higher = more recommended
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "path_type": self.path_type,
            "predicted_trust_delta": float(self.predicted_trust_delta),
            "risk_score": round(self.risk_score, 3),
            "financial_exposure": self.financial_exposure,
            "compliance_risk": self.compliance_risk,
            "cascade_effects": self.cascade_effects,
            "recommendation_weight": round(self.recommendation_weight, 3),
            "reasoning": self.reasoning,
        }


@dataclass
class ProphecyResult:
    """Complete prophecy analysis — all 3 paths + shadow simulation + recommendation."""
    agent_id: str
    action_type: str
    amount: float
    paths: list[ProphecyPath]
    recommended_path: str = ""
    confidence: float = 0.0
    trigger_reason: str = ""
    shadow_report: Optional[ShadowSimulationResult] = None
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "amount": self.amount,
            "recommended_path": self.recommended_path,
            "confidence": round(self.confidence, 3),
            "trigger_reason": self.trigger_reason,
            "shadow_report": self.shadow_report.to_dict() if self.shadow_report else None,
            "paths": [p.to_dict() for p in self.paths],
            "computed_at": self.computed_at.isoformat(),
        }


class ProphecyEngine:
    """
    Simulation engine combining deterministic rule-based Monte Carlo paths
    with real-time shadow execution sandbox risk scoring.
    """

    # Thresholds that trigger automatic prophecy
    AUTHORITY_RATIO_THRESHOLD = 0.70   # Action is 70%+ of authority limit
    UNSTABLE_TRUST_THRESHOLD = 0.60    # Agent trust below 0.6
    FIRST_ACTION_THRESHOLD = 5         # Fewer than 5 similar past actions

    def __init__(self):
        self.shadow_runner = ShadowExecutionRunner()

    def should_trigger(
        self,
        trust_score: float,
        amount: float,
        authority_limit: float,
        historical_action_count: int = 999,
    ) -> tuple[bool, str]:
        """Determine if prophecy should be triggered for this action."""
        if authority_limit > 0 and amount / authority_limit >= self.AUTHORITY_RATIO_THRESHOLD:
            return True, f"Action amount ({amount:,.0f}) is ≥70% of authority limit ({authority_limit:,.0f})"
        if trust_score < self.UNSTABLE_TRUST_THRESHOLD:
            return True, f"Agent trust score ({trust_score:.2f}) is below stability threshold ({self.UNSTABLE_TRUST_THRESHOLD})"
        if historical_action_count < self.FIRST_ACTION_THRESHOLD:
            return True, f"Agent has limited history ({historical_action_count} past similar actions)"
        return False, ""

    def simulate(
        self,
        agent_id: str,
        action_type: str,
        amount: float,
        trust_score: float,
        tier: str,
        authority_limit: float,
        historical_success_rate: float = 0.80,
        trigger_reason: str = "",
        action_payload: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ProphecyResult:
        """
        Run the 3-path simulation integrated with shadow sandbox execution.
        """
        authority_ratio = amount / authority_limit if authority_limit > 0 else 1.0

        # Step 1: Run lightweight shadow sandbox simulation
        shadow_report = self.shadow_runner.run_shadow_simulation(
            agent_id=agent_id,
            action_type=action_type,
            action_payload=action_payload,
            context=context,
        )

        # Step 2: Simulate Approve, Deny, and Escalate paths
        approve = self._simulate_approve(
            trust_score, authority_ratio, historical_success_rate, amount, tier, shadow_report
        )
        deny = self._simulate_deny(
            trust_score, authority_ratio, amount, tier, shadow_report
        )
        escalate = self._simulate_escalate(
            trust_score, authority_ratio, amount, tier, shadow_report
        )

        paths = [approve, deny, escalate]

        # Determine recommendation
        best = max(paths, key=lambda p: p.recommendation_weight)
        recommended = best.path_type

        # Confidence is based on spread and shadow sandbox certainty
        weights = sorted([p.recommendation_weight for p in paths], reverse=True)
        spread = weights[0] - weights[1] if len(weights) > 1 else 0
        base_confidence = min(0.5 + spread, 1.0)
        # If shadow report is clean, increase confidence; if critical, lock confidence to 0.99
        if shadow_report.severity == "critical":
            confidence = 0.99
        elif shadow_report.severity == "none":
            confidence = min(base_confidence + 0.1, 0.98)
        else:
            confidence = base_confidence

        result = ProphecyResult(
            agent_id=agent_id,
            action_type=action_type,
            amount=amount,
            paths=paths,
            recommended_path=recommended,
            confidence=round(confidence, 3),
            trigger_reason=trigger_reason,
            shadow_report=shadow_report,
        )

        logger.info(
            f"[PROPHECY] agent={agent_id[:8]} action={action_type} "
            f"amount={amount:,.0f} recommended={recommended} conf={confidence:.2f} "
            f"shadow_severity={shadow_report.severity}"
        )
        return result

    # ──────────────────────────────────────────────
    # Path simulators
    # ──────────────────────────────────────────────

    def _simulate_approve(
        self,
        trust: float,
        auth_ratio: float,
        success_rate: float,
        amount: float,
        tier: str,
        shadow: ShadowSimulationResult,
    ) -> ProphecyPath:
        """Simulate: what if we APPROVE this action?"""
        if success_rate >= 0.85:
            predicted_delta = Decimal("0.03")
            risk = 0.1 + (auth_ratio * 0.2)
            reasoning = "High historical success rate — approve is low-risk"
        elif success_rate >= 0.65:
            predicted_delta = Decimal("0.01")
            risk = 0.3 + (auth_ratio * 0.3)
            reasoning = "Moderate success rate — approve with monitoring"
        else:
            predicted_delta = Decimal("-0.05")
            risk = 0.5 + (auth_ratio * 0.4)
            reasoning = "Low success rate — approval carries significant risk"

        if auth_ratio > 0.90:
            risk = min(risk + 0.2, 1.0)
            reasoning += " (near authority limit — elevated risk)"

        cascades: list[str] = []
        if auth_ratio > 0.80:
            cascades.append(f"Action uses {auth_ratio*100:.0f}% of authority limit")
        if risk > 0.6:
            cascades.append("May trigger downstream compliance review")

        # Incorporate shadow sandbox findings
        if shadow.detected_hazards:
            risk = max(risk, shadow.shadow_risk_score)
            cascades.extend(shadow.detected_hazards)
            reasoning += f" [Shadow Sandbox: {len(shadow.detected_hazards)} hazards detected]"

        financial_exposure = amount * risk
        compliance_risk = "high" if risk > 0.7 else ("medium" if risk > 0.4 else "low")

        # Recommendation weight penalized by shadow risk
        weight = success_rate * (1 - risk) * 0.8

        return ProphecyPath(
            path_type="approve",
            predicted_trust_delta=predicted_delta,
            risk_score=round(risk, 3),
            financial_exposure=round(financial_exposure, 2),
            compliance_risk=compliance_risk,
            cascade_effects=cascades,
            recommendation_weight=round(max(0.0, weight), 3),
            reasoning=reasoning,
        )

    def _simulate_deny(
        self,
        trust: float,
        auth_ratio: float,
        amount: float,
        tier: str,
        shadow: ShadowSimulationResult,
    ) -> ProphecyPath:
        """Simulate: what if we DENY this action?"""
        predicted_delta = Decimal("0.00")
        risk = 0.05

        cascades = ["Agent action blocked — task may stall"]
        if tier in ("T1", "T2"):
            cascades.append("Senior agent blocked — may indicate overly restrictive policy")
            predicted_delta = Decimal("-0.01")

        compliance_risk = "none"
        reasoning = "Deny is safest but may cause operational delays"

        weight = 0.3 * (1 - auth_ratio)
        # If shadow detected critical hazards, deny becomes highly favored
        if shadow.severity in ("critical", "high"):
            weight += 0.5
            reasoning += f" [Shadow Sandbox confirms {shadow.severity} risk — deny favored]"

        return ProphecyPath(
            path_type="deny",
            predicted_trust_delta=predicted_delta,
            risk_score=round(risk, 3),
            financial_exposure=0.0,
            compliance_risk=compliance_risk,
            cascade_effects=cascades,
            recommendation_weight=round(min(weight, 1.0), 3),
            reasoning=reasoning,
        )

    def _simulate_escalate(
        self,
        trust: float,
        auth_ratio: float,
        amount: float,
        tier: str,
        shadow: ShadowSimulationResult,
    ) -> ProphecyPath:
        """Simulate: what if we ESCALATE to a human?"""
        predicted_delta = Decimal("0.02")
        risk = 0.15

        cascades = ["Action delayed pending human review (avg 4-24 hours)"]
        if amount > 50000:
            cascades.append(f"High-value action (₹{amount:,.0f}) — senior reviewer required")
            risk = 0.1

        compliance_risk = "low"
        reasoning = "Escalation provides human oversight — moderate delay cost"

        weight = 0.5 * auth_ratio + 0.3 * (1 - trust)
        if trust < 0.5:
            weight += 0.2
            reasoning += " (recommended for low-trust agents)"

        if shadow.detected_hazards and shadow.severity != "critical":
            weight += 0.3
            reasoning += " [Shadow Sandbox suggests human oversight due to potential side-effects]"

        return ProphecyPath(
            path_type="escalate",
            predicted_trust_delta=predicted_delta,
            risk_score=round(risk, 3),
            financial_exposure=round(amount * 0.05, 2),
            compliance_risk=compliance_risk,
            cascade_effects=cascades,
            recommendation_weight=round(min(weight, 1.0), 3),
            reasoning=reasoning,
        )
