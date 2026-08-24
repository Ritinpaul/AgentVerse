"""
tests/test_phase7_telemetry.py

Integration unit tests for Phase 7 State Plane Real-time Telemetry & ANCESTOR Traces:
- Event publishing with append-only sha256 state hashing
- ANCESTOR audit trace retrieval
- Step telemetry retrieval
"""

from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add state-plane app root to sys.path
sp_root = Path(__file__).resolve().parents[1]
if str(sp_root) not in sys.path:
    sys.path.insert(0, str(sp_root))

from app.main import app

client = TestClient(app)

EVENT_1 = {
    "runId": "run-p7-01",
    "agentId": "agent-test-01",
    "eventType": "ANCESTOR",
    "action": "POLICY_CHECK_SENTINEL",
    "verdict": "APPROVED",
    "risk_score": "LOW",
    "policy": "nuuvixx-standard-2026.09",
    "duration_ms": 12,
    "details": "Pre-flight SENTINEL policy check passed"
}

EVENT_2 = {
    "runId": "run-p7-01",
    "agentId": "agent-test-01",
    "eventType": "STEP",
    "action": "TOOL_CALL",
    "verdict": "APPROVED",
    "risk_score": "MEDIUM",
    "policy": "nuuvixx-standard-2026.09",
    "duration_ms": 140,
    "details": "Executed web_search tool",
    "step_data": {
        "step": 1,
        "tool": "web_search",
        "inputs": {"query": "AgentStudio docs"},
        "output": "Found 5 documentation results"
    }
}


def test_publish_telemetry_and_ancestor_traces():
    # 1. Publish Event 1
    resp1 = client.post("/telemetry/events", json=EVENT_1)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "published"
    assert data1["state_hash"].startswith("sha256:")

    hash1 = data1["state_hash"]

    # 2. Publish Event 2
    resp2 = client.post("/telemetry/events", json=EVENT_2)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "published"
    hash2 = data2["state_hash"]

    # Cryptographic link check: hash2 must differ from hash1
    assert hash1 != hash2

    # 3. Retrieve ANCESTOR traces
    anc_resp = client.get("/telemetry/runs/run-p7-01/ancestor")
    assert anc_resp.status_code == 200
    anc_data = anc_resp.json()
    assert anc_data["count"] == 2
    assert anc_data["traces"][0]["state_hash"] == hash1
    assert anc_data["traces"][1]["state_hash"] == hash2

    # 4. Retrieve Step Telemetry
    step_resp = client.get("/telemetry/runs/run-p7-01/steps")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["count"] == 1
    assert step_data["steps"][0]["step_data"]["tool"] == "web_search"
