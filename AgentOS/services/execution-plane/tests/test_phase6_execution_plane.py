"""
tests/test_phase6_execution_plane.py

Integration unit tests for Phase 6 Execution Plane Upgrade:
- Full Run State Machine transition tracking
- Server-Authoritative Runtime Policy Enforcement (Tool Risk, Network Egress, Budget Ceiling)
- Step Telemetry stream endpoints
- Cancellation flow
"""

from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add execution-plane app root to sys.path
ep_root = Path(__file__).resolve().parents[1]
if str(ep_root) not in sys.path:
    sys.path.insert(0, str(ep_root))

from app.main import app

client = TestClient(app)

VALID_MANIFEST = {
    "apiVersion": "agentstudio/v1",
    "kind": "Agent",
    "metadata": {
        "name": "phase6-test-agent",
        "version": "1.0.0"
    },
    "model": {
        "provider": "openai",
        "name": "gpt-4o"
    },
    "instructions": "Phase 6 execution plane test instructions",
    "tools": [
        {
            "id": "calculator",
            "type": "native",
            "risk": "low"
        }
    ],
    "policies": {
        "approval": {
            "criticalRiskToolCalls": "block",
            "highRiskToolCalls": "required"
        }
    },
    "budget": {
        "maxCostPerRun": 0.50
    },
    "runtime": {
        "sandbox": "docker",
        "egress": "restricted"
    }
}


def test_full_state_machine_execution():
    resp = client.post("/execute/v1/run", json={
        "agentId": "agent-p6-01",
        "manifest": VALID_MANIFEST
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["policyVerdict"] == "ALLOW"
    assert data["totalSteps"] >= 3

    run_id = data["runId"]

    # Test status endpoint
    st_resp = client.get(f"/execute/v1/runs/{run_id}/status")
    assert st_resp.status_code == 200
    st_data = st_resp.json()
    assert st_data["status"] == "COMPLETED"
    assert len(st_data["stateHistory"]) >= 6  # QUEUED -> VALIDATING -> POLICY_CHECK -> SCHEDULING -> SANDBOX_PROVISIONING -> RUNNING -> COMPLETED

    # Test telemetry step stream endpoint
    steps_resp = client.get(f"/execute/v1/runs/{run_id}/steps")
    assert steps_resp.status_code == 200
    steps_data = steps_resp.json()
    assert len(steps_data["steps"]) >= 3
    assert steps_data["steps"][0]["action"] == "THOUGHT"
    assert steps_data["steps"][-1]["action"] == "OUTPUT"


def test_critical_risk_tool_blocked_by_policy():
    critical_manifest = dict(VALID_MANIFEST)
    critical_manifest["tools"] = [
        {
            "id": "delete-db-table",
            "type": "native",
            "risk": "critical"
        }
    ]

    resp = client.post("/execute/v1/run", json={
        "agentId": "agent-p6-02",
        "manifest": critical_manifest
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "BLOCKED"
    assert "criticalRiskToolCalls" in data["denialReason"]

    # Verify telemetry steps contain BLOCKED action
    steps_resp = client.get(f"/execute/v1/runs/{data['runId']}/steps")
    blocked_step = [s for s in steps_resp.json()["steps"] if s["action"] == "BLOCKED"]
    assert len(blocked_step) == 1
    assert "CRITICAL risk" in blocked_step[0]["output"]


def test_unlisted_domain_blocked_by_egress_policy():
    egress_manifest = dict(VALID_MANIFEST)
    egress_manifest["tools"] = [
        {
            "id": "fetch-api",
            "type": "http",
            "risk": "low",
            "permissions": {
                "egress": ["api.allowed.com"]
            }
        }
    ]

    # Simulate tool call to unlisted domain
    resp = client.post("/execute/v1/run", json={
        "agentId": "agent-p6-03",
        "manifest": egress_manifest,
        "simulate_tool_calls": [
            {
                "id": "fetch-api",
                "type": "http",
                "risk": "low",
                "inputs": {"url": "https://malicious-evade.com/data"},
                "permissions": {"egress": ["api.allowed.com"]}
            }
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "BLOCKED"
    assert "not in allowed egress whitelist" in data["denialReason"]


def test_budget_exceeded_error():
    low_budget_manifest = dict(VALID_MANIFEST)
    low_budget_manifest["budget"] = {"maxCostPerRun": 0.005}

    resp = client.post("/execute/v1/run", json={
        "agentId": "agent-p6-04",
        "manifest": low_budget_manifest,
        "simulate_tool_calls": [
            {
                "id": "expensive-llm-call",
                "type": "native",
                "risk": "low",
                "estimated_cost": 0.10
            }
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert "exceeds max allowed budget" in data["denialReason"]


def test_cancel_run():
    # Create run instance in manager
    from app.sandbox.run_state_machine import run_manager
    run_inst = run_manager.create_run("agent-p6-05", VALID_MANIFEST)
    run_inst._record_state_change("RUNNING")

    cancel_resp = client.post(f"/execute/v1/runs/{run_inst.run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    st_resp = client.get(f"/execute/v1/runs/{run_inst.run_id}/status")
    assert st_resp.json()["status"] == "CANCELLED"
