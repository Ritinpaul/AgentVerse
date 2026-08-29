import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.session import get_db
from app.db.base import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

VALID_AGENT_YAML = """name: sec-test-agent
version: 1.0.0
description: Enterprise security test agent.
framework: custom
model:
  provider: anthropic
  name: claude-3-5-sonnet
  temperature: 0.2
tools:
  - type: mcp
    server: zendesk
    tool: get-ticket
"""

def test_api_key_auth_guard(monkeypatch):
    """Verify X-API-Key authentication requirement on publish endpoint."""
    monkeypatch.setenv("AGENTSTORE_API_KEYS", "secret-key-1,secret-key-2")

    payload = {
        "builder_id": "sec-team",
        "agent_yaml": VALID_AGENT_YAML,
        "category": "security"
    }

    # 1. Missing X-API-Key -> 401 Unauthorized
    res_no_key = client.post("/api/v1/registry/agents", json=payload)
    assert res_no_key.status_code == 401
    assert "Missing authentication credentials" in res_no_key.json()["detail"]

    # 2. Invalid X-API-Key -> 401 Unauthorized
    res_wrong_key = client.post("/api/v1/registry/agents", json=payload, headers={"X-API-Key": "wrong-key"})
    assert res_wrong_key.status_code == 401

    # 3. Valid X-API-Key -> 201 Created
    res_valid_key = client.post("/api/v1/registry/agents", json=payload, headers={"X-API-Key": "secret-key-1"})
    assert res_valid_key.status_code == 201, res_valid_key.text
    assert res_valid_key.json()["slug"] == "sec-team/sec-test-agent"


def test_payload_size_limit_guard(monkeypatch):
    """Verify payload size ceiling enforcement (64 KB cap)."""
    monkeypatch.setenv("AGENTSTORE_API_KEYS", "secret-key-1")

    large_comment = "# " + ("A" * 70_000) + "\n"
    oversized_yaml = VALID_AGENT_YAML + large_comment

    payload = {
        "builder_id": "sec-team",
        "agent_yaml": oversized_yaml,
        "category": "security"
    }

    response = client.post(
        "/api/v1/registry/agents",
        json=payload,
        headers={"X-API-Key": "secret-key-1"}
    )
    assert response.status_code == 422
    assert "exceeds" in str(response.json())


def test_initial_trust_score_zero(monkeypatch):
    """Verify newly published agents start with initial unverified trust_score = 0.0."""
    monkeypatch.setenv("AGENTSTORE_API_KEYS", "secret-key-1")

    payload = {
        "builder_id": "sec-team",
        "agent_yaml": VALID_AGENT_YAML,
        "category": "security"
    }
    response = client.post(
        "/api/v1/registry/agents",
        json=payload,
        headers={"X-API-Key": "secret-key-1"}
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["trust_score"] == 0.0


def test_cors_origins_security():
    """Verify CORS response header handling."""
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3051"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3051"


def test_retract_version_auth_guard(monkeypatch):
    """Verify retract version endpoint is protected by API key auth guard and ownership rules."""
    monkeypatch.setenv("AGENTSTORE_API_KEYS", "prod-key")

    # Publish initially with auth key
    res_pub = client.post(
        "/api/v1/registry/agents",
        json={
            "builder_id": "sec-team",
            "agent_yaml": VALID_AGENT_YAML,
            "category": "security"
        },
        headers={"X-API-Key": "prod-key"}
    )
    assert res_pub.status_code == 201, res_pub.text

    # Retract without key -> 401
    res_unauth = client.delete("/api/v1/registry/agents/sec-team/sec-test-agent/versions/1.0.0")
    assert res_unauth.status_code == 401

    # Retract with valid key -> 200
    res_auth = client.delete(
        "/api/v1/registry/agents/sec-team/sec-test-agent/versions/1.0.0",
        headers={"X-API-Key": "prod-key"}
    )
    assert res_auth.status_code == 200
    assert "retracted" in res_auth.json()["message"]


def test_rbac_ownership_violation_guard(monkeypatch):
    """Verify RBAC ownership constraint: builder cannot modify another org's agent."""
    monkeypatch.setenv("AGENTSTORE_API_KEYS", "secret-key-1")

    # 1. Publish agent under 'org-alpha'
    res_pub = client.post(
        "/api/v1/registry/agents",
        json={
            "builder_id": "org-alpha",
            "agent_yaml": VALID_AGENT_YAML,
            "category": "security"
        },
        headers={"X-API-Key": "secret-key-1", "X-User-Org": "org-alpha"}
    )
    assert res_pub.status_code == 201

    v2_yaml = VALID_AGENT_YAML.replace("version: 1.0.0", "version: 1.0.1")

    # 2. Attempt to publish a new version under 'org-beta' for 'org-alpha/sec-test-agent' -> 403 Forbidden
    res_cross_org = client.post(
        "/api/v1/registry/agents/org-alpha/sec-test-agent/versions",
        json={
            "version": "1.0.1",
            "changelog": "Unauthorized update",
            "agent_yaml": v2_yaml
        },
        headers={"X-API-Key": "secret-key-1", "X-User-Org": "org-beta"}
    )
    assert res_cross_org.status_code == 403
    assert "Ownership violation" in res_cross_org.json()["detail"]



