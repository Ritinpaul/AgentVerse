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


def test_list_templates():
    """Verify GET /registry/templates returns verified starter templates."""
    response = client.get("/api/v1/registry/templates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4

    # Check that required template keys exist
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "category" in first
    assert "capabilities" in first
    assert isinstance(first["capabilities"], list)


def test_filter_templates_by_capability():
    """Verify capability-based filtering works (e.g. x402-escrow, finops)."""
    response = client.get("/api/v1/registry/templates?capability=x402-escrow")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any("x402-escrow" in t["capabilities"] for t in data)


def test_filter_templates_by_category():
    """Verify category filtering works."""
    response = client.get("/api/v1/registry/templates?category=DevOps")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all("DevOps" in t["category"] for t in data)


def test_get_single_template_detail():
    """Verify GET /registry/templates/{id} returns template manifests and files."""
    response = client.get("/api/v1/registry/templates/finance")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "finance"
    assert "x402-escrow" in data["capabilities"]
    assert "files" in data
    assert "agent.yaml" in data["files"]
    assert "tools.py" in data["files"]


def test_get_nonexistent_template_returns_404():
    """Verify 404 for unknown template."""
    response = client.get("/api/v1/registry/templates/unknown-template-xyz")
    assert response.status_code == 404


def test_fork_template_interpolation():
    """Verify POST /registry/templates/{id}/fork replaces ${name} and ${slug}."""
    payload = {
        "name": "Acme Treasury Sentinel",
        "slug": "acme-treasury-sentinel"
    }
    response = client.post("/api/v1/registry/templates/finance/fork", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Acme Treasury Sentinel"
    assert data["slug"] == "acme-treasury-sentinel"
    assert "files" in data
    assert "agent.yaml" in data["files"]

    manifest = data["files"]["agent.yaml"]
    assert "name: Acme Treasury Sentinel" in manifest
    assert "slug: acme-treasury-sentinel" in manifest
    assert "${name}" not in manifest
    assert "${slug}" not in manifest
