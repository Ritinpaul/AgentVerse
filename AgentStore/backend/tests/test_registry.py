import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.session import get_db
from app.db.base import Base

# In-memory database with StaticPool for isolated unit testing
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

VALID_AGENT_YAML = """name: support-agent
version: 1.0.0
description: Enterprise customer support agent with Zendesk integration.
framework: langchain
model:
  provider: anthropic
  name: claude-3-5-sonnet
  temperature: 0.2
tools:
  - type: mcp
    server: zendesk
    tool: get-ticket
"""

INVALID_AGENT_YAML = """name: bad-agent
# missing required version, description, framework, and model
"""

AUTH_HEADERS = {"X-API-Key": "dev-admin-key-2026"}

def test_publish_agent_success():
    payload = {
        "builder_id": "acme-corp",
        "agent_yaml": VALID_AGENT_YAML,
        "category": "support"
    }
    response = client.post("/api/v1/registry/agents", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["slug"] == "acme-corp/support-agent"
    assert data["current_version"] == "1.0.0"
    assert data["category"] == "support"
    assert data["trust_score"] == 0.0

def test_publish_agent_invalid_yaml():
    payload = {
        "builder_id": "acme-corp",
        "agent_yaml": INVALID_AGENT_YAML,
        "category": "support"
    }
    response = client.post("/api/v1/registry/agents", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422
    assert "errors" in response.json()["detail"]

def test_publish_version_and_search():
    # Publish initial agent
    payload = {
        "builder_id": "acme-corp",
        "agent_yaml": VALID_AGENT_YAML,
        "category": "support"
    }
    client.post("/api/v1/registry/agents", json=payload, headers=AUTH_HEADERS)

    # Publish v1.1.0
    v2_yaml = VALID_AGENT_YAML.replace("version: 1.0.0", "version: 1.1.0").replace("Zendesk integration.", "Zendesk & Salesforce integration.")
    v2_payload = {
        "agent_yaml": v2_yaml,
        "changelog": "Added Salesforce support."
    }
    res_ver = client.post("/api/v1/registry/agents/acme-corp/support-agent/versions", json=v2_payload, headers=AUTH_HEADERS)
    assert res_ver.status_code == 201, res_ver.text
    assert res_ver.json()["version_semver"] == "1.1.0"

    # Verify search
    res_search = client.get("/api/v1/search?q=salesforce")
    assert res_search.status_code == 200
    results = res_search.json()
    assert len(results) == 1
    assert results[0]["current_version"] == "1.1.0"

def test_cli_install_and_run():
    payload = {
        "builder_id": "acme-corp",
        "agent_yaml": VALID_AGENT_YAML,
        "category": "support"
    }
    client.post("/api/v1/registry/agents", json=payload, headers=AUTH_HEADERS)

    res_install = client.post("/api/v1/cli/install", json={"slug": "acme-corp/support-agent"})
    assert res_install.status_code == 200
    data = res_install.json()
    assert data["slug"] == "acme-corp/support-agent"
    assert "nuuvixx run" in data["instructions"][-1]

    res_run = client.get("/api/v1/cli/run/acme-corp/support-agent")
    assert res_run.status_code == 200
    assert "nuuvixx" in res_run.json()["command"]
