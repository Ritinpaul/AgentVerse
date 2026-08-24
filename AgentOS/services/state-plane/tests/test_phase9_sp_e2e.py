"""
tests/test_phase9_sp_e2e.py

Phase 9 — State Plane E2E Integration Tests
============================================

Validates the full real-time telemetry & ANCESTOR hash chain pipeline:
  - Health check
  - Publish two ANCESTOR telemetry events
  - Verify hash chain: h2 ≠ h1 (each event gets a unique chained hash)
  - Retrieve ANCESTOR log and confirm ordering and hash values
  - Step telemetry endpoint
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ── State bag ──────────────────────────────────────────────────────────────────

class _SP:
    hash_1: str | None = None
    hash_2: str | None = None


_state = _SP()

RUN_ID = "e2e-sp-phase9-001"


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_sp_01_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "state-plane"


def test_sp_02_publish_first_ancestor_event():
    ev = {
        "runId": RUN_ID,
        "agentId": "nuuvixx/e2e-research-agent",
        "eventType": "ANCESTOR",
        "action": "SENTINEL_POLICY_PRE_FLIGHT",
        "verdict": "APPROVED",
        "risk_score": "LOW",
        "policy": "nuuvixx-standard-2026.09",
        "duration_ms": 9,
        "details": "Pre-flight SENTINEL check passed"
    }
    r = client.post("/telemetry/events", json=ev)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "published"
    assert d["state_hash"].startswith("sha256:")
    _state.hash_1 = d["state_hash"]


def test_sp_03_publish_second_ancestor_event():
    ev = {
        "runId": RUN_ID,
        "agentId": "nuuvixx/e2e-research-agent",
        "eventType": "ANCESTOR",
        "action": "TOOL_CALL_WEB_SEARCH",
        "verdict": "APPROVED",
        "risk_score": "LOW",
        "policy": "nuuvixx-standard-2026.09",
        "duration_ms": 175,
        "details": "web-search tool invoked and approved"
    }
    r = client.post("/telemetry/events", json=ev)
    assert r.status_code == 200
    d = r.json()
    assert d["state_hash"].startswith("sha256:")
    _state.hash_2 = d["state_hash"]


def test_sp_04_hash_chain_is_unique():
    """Each event in the ANCESTOR chain must produce a cryptographically distinct hash."""
    assert _state.hash_1 is not None, "hash_1 not set"
    assert _state.hash_2 is not None, "hash_2 not set"
    assert _state.hash_1 != _state.hash_2, (
        "ANCESTOR hash chain must produce distinct hashes for each event — "
        f"both returned {_state.hash_1}"
    )


def test_sp_05_ancestor_trace_log_order_and_hashes():
    r = client.get(f"/telemetry/runs/{RUN_ID}/ancestor")
    assert r.status_code == 200
    d = r.json()
    assert d["count"] == 2
    # The API returns 'runId' (camelCase)
    assert d["runId"] == RUN_ID
    traces = d["traces"]
    # Verify ordering: first event is first in log
    assert traces[0]["action"] == "SENTINEL_POLICY_PRE_FLIGHT"
    assert traces[1]["action"] == "TOOL_CALL_WEB_SEARCH"
    # Verify hash chain values match what was returned during publish
    assert traces[0]["state_hash"] == _state.hash_1
    assert traces[1]["state_hash"] == _state.hash_2
    # All hashes must be valid sha256: prefixed strings
    for t in traces:
        assert t["state_hash"].startswith("sha256:")


def test_sp_06_step_telemetry_endpoint():
    """Step telemetry endpoint returns an empty list for ANCESTOR-only run (no STEP events)."""
    r = client.get(f"/telemetry/runs/{RUN_ID}/steps")
    assert r.status_code == 200
    d = r.json()
    assert "count" in d
    assert isinstance(d["steps"], list)
