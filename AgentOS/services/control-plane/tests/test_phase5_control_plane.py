"""
tests/test_phase5_control_plane.py

Integration unit tests for Phase 5 Control Plane API Hardening:
- Schema validation via AgentManifest Pydantic model
- Content-addressed sha256 manifest hashing
- Immutable version registration
- Run execution referencing immutable versions
- Server-authoritative SENTINEL policy check enforcement (denying excessive budgets)
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Add control-plane app root to sys.path
cp_root = Path(__file__).resolve().parents[1]
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from app.main import app
from app.routers.lifecycle import get_session


# Setup in-memory SQLite database for testing
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


VALID_YAML = """
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: phase5-agent
  version: 1.0.0
model:
  provider: openai
  name: gpt-4o
instructions: "Test prompt"
tools:
  - id: web-search
    type: mcp
    server: mcp-search
    tool: search
budget:
  maxCostPerRun: 0.25
"""

INVALID_YAML = """
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: INVALID NAME WITH SPACES!
  version: not-a-semver
model:
  provider: unknown_provider
"""

EXCESSIVE_BUDGET_YAML = """
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: excessive-agent
  version: 1.0.0
model:
  provider: openai
  name: gpt-4o
instructions: "Unbounded prompt"
budget:
  maxCostPerRun: 50.0
"""


def test_validate_valid_manifest(client: TestClient):
    resp = client.post("/v1/agents/validate", json={"yamlContent": VALID_YAML})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["canonicalHash"].startswith("sha256:")


def test_validate_invalid_manifest(client: TestClient):
    resp = client.post("/v1/agents/validate", json={"yamlContent": INVALID_YAML})
    assert resp.status_code == 422


def test_plan_manifest(client: TestClient):
    resp = client.post("/v1/agents/plan", json={"yamlContent": VALID_YAML})
    assert resp.status_code == 200
    data = resp.json()
    assert data["canonicalHash"].startswith("sha256:")
    assert data["policyVerdict"] == "ALLOW"
    assert data["estimatedCostUsd"] == 0.25


def test_create_version_and_run(client: TestClient):
    # 1. Create Immutable Agent Version
    v_resp = client.post("/v1/agents/versions", json={"agent_name": "phase5-agent", "yamlContent": VALID_YAML})
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert "versionId" in v_data
    assert v_data["manifestHash"].startswith("sha256:")

    version_id = v_data["versionId"]

    # Test Idempotency: duplicate version request returns same versionId
    v_resp2 = client.post("/v1/agents/versions", json={"agent_name": "phase5-agent", "yamlContent": VALID_YAML})
    assert v_resp2.json()["versionId"] == version_id
    assert v_resp2.json()["created"] is False

    # 2. Queue Run referencing immutable versionId
    r_resp = client.post("/v1/runs", json={"agentVersionId": version_id, "input_text": "Run query"})
    assert r_resp.status_code == 200
    r_data = r_resp.json()
    assert r_data["status"] == "QUEUED"
    assert r_data["policyVerdict"] == "ALLOW"

    run_id = r_data["runId"]

    # 3. Get Run status
    get_resp = client.get(f"/v1/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["runId"] == run_id
    assert get_resp.json()["status"] == "QUEUED"


def test_run_blocked_by_sentinel_policy(client: TestClient):
    # Create version with excessive budget
    v_resp = client.post("/v1/agents/versions", json={"agent_name": "excessive-agent", "yamlContent": EXCESSIVE_BUDGET_YAML})
    version_id = v_resp.json()["versionId"]

    # Run start should be BLOCKED (403) by server-authoritative SENTINEL check
    r_resp = client.post("/v1/runs", json={"agentVersionId": version_id})
    assert r_resp.status_code == 403
    detail = r_resp.json()["detail"]
    assert "BLOCKED" in detail["message"]
    assert len(detail["reasons"]) > 0
