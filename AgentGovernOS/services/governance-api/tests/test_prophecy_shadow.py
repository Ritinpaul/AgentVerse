"""
Unit tests for Prophecy Engine with Shadow Execution Sandbox.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from policy.prophecy import ProphecyEngine, ShadowExecutionRunner


def test_shadow_execution_clean_action():
    runner = ShadowExecutionRunner()
    action = {"type": "read_metrics", "query": "SELECT cpu FROM agent_stats"}

    report = runner.run_shadow_simulation("agent-clean", "read_metrics", action)
    assert report.executed is True
    assert report.severity == "none"
    assert report.shadow_risk_score == 0.05
    assert len(report.detected_hazards) == 0


def test_shadow_execution_destructive_mutation_detected():
    runner = ShadowExecutionRunner()
    action = {"type": "execute_command", "cmd": "DROP TABLE users CASCADE;"}

    report = runner.run_shadow_simulation("agent-rogue", "execute_command", action)
    assert report.executed is True
    assert report.severity == "critical"
    assert report.shadow_risk_score >= 0.90
    assert any("Destructive mutation" in h for h in report.detected_hazards)


def test_shadow_execution_unapproved_egress_detected():
    runner = ShadowExecutionRunner()
    action = {"type": "http_request", "target_url": "https://unauthorized-evil-data-collector.com/exfil"}

    report = runner.run_shadow_simulation("agent-exfil", "http_request", action)
    assert report.executed is True
    assert report.severity in ("high", "critical")
    assert any("Unapproved external network egress" in h for h in report.detected_hazards)


def test_prophecy_simulate_incorporates_shadow_sandbox():
    engine = ProphecyEngine()

    # Safe action with high trust
    safe_result = engine.simulate(
        agent_id="agent-trusted",
        action_type="calculate_tax",
        amount=5000.0,
        trust_score=0.90,
        tier="T2",
        authority_limit=50000.0,
        action_payload={"tax_year": 2026},
    )

    assert safe_result.recommended_path == "approve"
    assert safe_result.shadow_report is not None
    assert safe_result.shadow_report.severity == "none"
    assert safe_result.confidence >= 0.70

    # Hazardous action with destructive SQL
    hazard_result = engine.simulate(
        agent_id="agent-attacker",
        action_type="db_migration",
        amount=1000.0,
        trust_score=0.65,
        tier="T3",
        authority_limit=50000.0,
        action_payload={"sql": "DROP TABLE ledger;"},
    )

    assert hazard_result.recommended_path in ("deny", "escalate")
    assert hazard_result.shadow_report is not None
    assert hazard_result.shadow_report.severity == "critical"
    approve_path = next(p for p in hazard_result.paths if p.path_type == "approve")
    assert "Shadow Sandbox" in approve_path.reasoning
    assert approve_path.risk_score >= 0.90
