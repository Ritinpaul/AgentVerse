"""
tests/test_phase8_publishing.py

Integration unit tests for Phase 8 Control Plane Server-Authoritative Registry Publishing Pipeline:
- Server-authoritative manifest validation & canonical sha256 manifest hashing
- Pre-publish SENTINEL policy check enforcement
- Automated SBOM generation & digital signature minting
- Immutable ReleaseRecord DB persistence & query endpoints
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


PUBLISHABLE_YAML = """
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: phase8-agent
  version: 1.2.0
model:
  provider: anthropic
  name: claude-3-5-sonnet
instructions: "Production research assistant prompt"
tools:
  - id: web-search
    type: mcp
    server: mcp-search
    tool: search
    risk: low
budget:
  maxCostPerRun: 0.40
"""

DENIED_PUBLISH_YAML = """
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: illegal-agent
  version: 1.0.0
model:
  provider: openai
  name: gpt-4o
instructions: "Unbounded directive"
budget:
  maxCostPerRun: 99.0
"""


def test_publish_agent_release(client: TestClient):
    # 1. Publish Release
    resp = client.post("/v1/registry/publish", json={
        "yamlContent": PUBLISHABLE_YAML,
        "orgSlug": "nuuvixx"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] is True
    assert data["agentSlug"] == "nuuvixx/phase8-agent"
    assert data["version"] == "1.2.0"
    assert data["manifestHash"].startswith("sha256:")
    assert data["signature"].startswith("sha256:sig_")
    assert "components" in data["sbomJson"]

    release_id = data["releaseId"]

    # 2. Test Idempotency: duplicate publish returns created: false
    resp2 = client.post("/v1/registry/publish", json={
        "yamlContent": PUBLISHABLE_YAML,
        "orgSlug": "nuuvixx"
    })
    assert resp2.status_code == 200
    assert resp2.json()["created"] is False
    assert resp2.json()["releaseId"] == release_id

    # 3. List Releases
    list_resp = client.get("/v1/registry/releases")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] >= 1

    # 4. Get Release by ID
    get_resp = client.get(f"/v1/registry/releases/{release_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["agentSlug"] == "nuuvixx/phase8-agent"
    assert get_data["signature"].startswith("sha256:sig_")
    assert len(get_data["sbomJson"]["components"]) >= 2

    # 5. Query Releases by Agent Slug
    slug_resp = client.get("/v1/registry/agents/nuuvixx/phase8-agent")
    assert slug_resp.status_code == 200
    assert slug_resp.json()["count"] == 1


def test_publish_denied_by_policy(client: TestClient):
    resp = client.post("/v1/registry/publish", json={
        "yamlContent": DENIED_PUBLISH_YAML,
        "orgSlug": "nuuvixx"
    })
    assert resp.status_code == 403
    assert "DENIED by GovernOS SENTINEL policy" in resp.json()["detail"]
