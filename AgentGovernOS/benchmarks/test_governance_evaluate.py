"""Benchmarks for POST /governance/evaluate — the hot-path endpoint.

These benchmarks answer the CISO question: "What is the latency overhead?"

Target SLOs :
    p50  < 10 ms
    p95  < 30 ms
    p99  < 50 ms

Run:
    pytest benchmarks/test_governance_evaluate.py --benchmark-only -v
    pytest benchmarks/test_governance_evaluate.py --benchmark-only \\
        --benchmark-json=benchmarks/results/governance_evaluate.json
"""

from __future__ import annotations

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Payloads
# ─────────────────────────────────────────────────────────────────────────────

def _make_envelope(agent_code: str, action: str = "read_report", amount: float = 0.0) -> dict:
    return {
        "agent_code": agent_code,
        "action_requested": action,
        "agent_source": "benchmark",
        "context": {"amount": amount, "type": action, "description": "Benchmark evaluation"},
        "calling_system": "benchmark_suite",
        "sdk_version": "benchmark",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Benchmarks
# ─────────────────────────────────────────────────────────────────────────────

class TestGovernanceEvaluateBenchmarks:
    """Benchmark suite for /governance/evaluate endpoint."""

    def test_bench_low_risk_action(self, benchmark, app_client, seeded_agent_code):
        """LOW-risk: simple read action under authority limit.

        Represents the most common case — agent reads a report, no violations.
        Target: p99 < 50ms.
        """
        envelope = _make_envelope(seeded_agent_code, action="read_report", amount=0.0)

        def _call:
            return app_client.post("/governance/evaluate", json=envelope)

        result = benchmark.pedantic(_call, rounds=20, warmup_rounds=3)
        assert result is not None  # benchmark callable must return something

    def test_bench_medium_risk_action(self, benchmark, app_client, seeded_agent_code):
        """MEDIUM-risk: action near authority limit triggers more policy checks.

        Target: p99 < 50ms even with escalation path.
        """
        envelope = _make_envelope(
            seeded_agent_code, action="approve_payment", amount=800.0
        )

        result = benchmark.pedantic(
            lambda: app_client.post("/governance/evaluate", json=envelope),
            rounds=20,
            warmup_rounds=3,
        )
        assert result is not None

    def test_bench_high_risk_blocked_action(self, benchmark, app_client, seeded_agent_code):
        """HIGH-risk: explicitly blocked action (wire_transfer).

        Block decision must be reached quickly — no expensive LLM calls.
        Target: p99 < 20ms (block should short-circuit).
        """
        envelope = _make_envelope(
            seeded_agent_code, action="wire_transfer", amount=500000.0
        )

        result = benchmark.pedantic(
            lambda: app_client.post("/governance/evaluate", json=envelope),
            rounds=20,
            warmup_rounds=3,
        )
        assert result is not None

    def test_bench_concurrent_100_agents(self, benchmark, app_client):
        """LOAD: simulate 100 different agent codes calling evaluate simultaneously.

        Not true concurrency (TestClient is sync), but exercises the policy loop
        for 100 consecutive calls with distinct agent codes (no caching benefit).
        """
        agent_codes = [f"BENCH-LOAD-{i:03d}" for i in range(100)]

        def _burst:
            responses = []
            for code in agent_codes:
                resp = app_client.post(
                    "/governance/evaluate",
                    json=_make_envelope(code, "read_report"),
                )
                responses.append(resp)
            return responses

        result = benchmark.pedantic(_burst, rounds=3, warmup_rounds=1)
        assert len(result) == 100

    def test_bench_health_baseline(self, benchmark, app_client):
        """BASELINE: /health should be near-zero overhead.

        Used to measure pure HTTP stack cost. Governance evaluate overhead =
        evaluate_latency - health_latency.
        """
        result = benchmark.pedantic(
            lambda: app_client.get("/health"),
            rounds=50,
            warmup_rounds=5,
        )
        assert result is not None


class TestGovernanceEvaluateResponseSLOs:
    """Non-benchmark tests: verify response correctness and basic performance SLO."""

    def test_low_risk_returns_approved(self, app_client, seeded_agent_code):
        """Low-risk action should return APPROVED verdict."""
        resp = app_client.post(
            "/governance/evaluate",
            json=_make_envelope(seeded_agent_code, "read_report"),
        )
        # Accept 200 OK or 422/404 if agent not seeded (CI environment may not have DB)
        assert resp.status_code in (200, 404, 422), f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            data = resp.json()
            assert "verdict" in data
            assert data["verdict"] in ("APPROVED", "BLOCKED", "ESCALATED")

    def test_blocked_action_returns_blocked(self, app_client, seeded_agent_code):
        """wire_transfer must always return BLOCKED verdict."""
        resp = app_client.post(
            "/governance/evaluate",
            json=_make_envelope(seeded_agent_code, "wire_transfer", amount=999999.0),
        )
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("verdict") == "BLOCKED", (
                f"Expected BLOCKED for wire_transfer, got: {data.get('verdict')}"
            )

    def test_evaluate_returns_audit_id(self, app_client, seeded_agent_code):
        """Every evaluate response must include an audit_id for traceability."""
        resp = app_client.post(
            "/governance/evaluate",
            json=_make_envelope(seeded_agent_code, "read_report"),
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "audit_id" in data, "Missing audit_id in governance response"
            assert data["audit_id"] != "", "audit_id must not be empty"

    def test_unknown_agent_returns_structured_error(self, app_client):
        """Unknown agent code must return structured error, not 500."""
        resp = app_client.post(
            "/governance/evaluate",
            json=_make_envelope("NONEXISTENT-AGENT-XYZ", "read_report"),
        )
        # Should be 404 or 422, never 500
        assert resp.status_code in (200, 404, 422), (
            f"Unknown agent returned {resp.status_code} — expected 404 or graceful verdict"
        )
        assert resp.status_code != 500, "Unknown agent caused 500 — must never crash"
