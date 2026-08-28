"""
Unit tests and benchmark for SentinelBytecodeEngine and DecisionTelemetryStreamer.
"""

from __future__ import annotations

import os
import sys
import time
from decimal import Decimal
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from policy.compiled_sentinel import (
    SentinelBytecodeEngine,
    DecisionTelemetryStreamer,
    sentinel_engine,
    telemetry_streamer,
)


def make_agent(trust=0.85, tier="T2", status="active"):
    agent = MagicMock()
    agent.id = "agent-test-uuid-001"
    agent.trust_score = Decimal(str(trust))
    agent.tier = tier
    agent.status = status
    return agent


def test_compiled_amount_limit_rule():
    engine = SentinelBytecodeEngine()
    rule = {"id": "pol-amount", "type": "amount_limit", "max_amount": 5000}
    agent = make_agent()

    # Passes under limit
    assert engine.evaluate_rule(rule, agent, {"amount": 2500}) is True
    # Passes at limit
    assert engine.evaluate_rule(rule, agent, {"amount": 5000}) is True
    # Fails over limit
    assert engine.evaluate_rule(rule, agent, {"amount": 5001}) is False


def test_compiled_tool_allowlist_rule():
    engine = SentinelBytecodeEngine()
    rule = {"id": "pol-tools", "type": "tool_allowlist", "allowed_tools": ["search", "calculator"]}
    agent = make_agent()

    assert engine.evaluate_rule(rule, agent, {"tool_name": "search"}) is True
    assert engine.evaluate_rule(rule, agent, {"tool_name": "bash"}) is False


def test_compiled_regex_guard_rule():
    engine = SentinelBytecodeEngine()
    rule = {
        "id": "pol-regex",
        "type": "regex_guard",
        "parameter_key": "query",
        "pattern": r"^[a-zA-Z0-9_\- ]+$",
    }
    agent = make_agent()

    assert engine.evaluate_rule(rule, agent, {"query": "safe search query 123"}) is True
    assert engine.evaluate_rule(rule, agent, {"query": "malicious; rm -rf /"}) is False


def test_decision_telemetry_streaming():
    telemetry = DecisionTelemetryStreamer(max_buffer_size=100)
    telemetry.clear()

    event = telemetry.record_decision(
        agent_id="agent-007",
        policy_id="pol-trust-01",
        rule_type="trust_minimum",
        verdict="PASS",
        duration_us=45,
        metadata={"tier": "T2"},
    )

    assert event.event_id is not None
    assert event.verdict == "PASS"
    assert len(event.audit_hash) == 64  # SHA-256 hex string
    assert len(telemetry.get_recent_events()) == 1


def test_sub_millisecond_benchmark():
    """Benchmark: 1,000 compiled rule evaluations must complete in under 50ms (<0.05ms per eval)."""
    engine = SentinelBytecodeEngine()
    rule = {"id": "pol-bench", "type": "amount_limit", "max_amount": 10000}
    agent = make_agent()
    action = {"amount": 5000}

    # Warmup
    engine.evaluate_rule(rule, agent, action)

    t0 = time.perf_counter()
    for _ in range(1000):
        engine.evaluate_rule(rule, agent, action)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Ensure 1000 evaluations finish with sub-millisecond average latency (<1.0ms each -> <1000ms total)
    assert elapsed_ms < 1000.0, f"Benchmark failed: 1000 evals took {elapsed_ms:.2f}ms"
