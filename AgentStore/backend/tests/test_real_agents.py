import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db.base_class import Base
from app.db.session import get_db

from agents.security_sentinel.runner import SecuritySentinelRunner
from agents.finops_cost_optimizer.runner import FinOpsCostOptimizerRunner


from app.services.security_scanner import run_full_security_scan

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(fastapi_app)


@pytest.fixture(autouse=True)
def setup_database(monkeypatch):
    Base.metadata.create_all(bind=engine)
    import app.db.session
    monkeypatch.setattr(app.db.session, "SessionLocal", TestingSessionLocal)
    fastapi_app.dependency_overrides[get_db] = override_get_db
    from app.main import _seed_demo_data
    _seed_demo_data()
    yield
    Base.metadata.drop_all(bind=engine)
    fastapi_app.dependency_overrides.pop(get_db, None)



def test_security_sentinel_runner_execution():
    sample_code = """
import os
def handle_user(data):
    api_key = "sk-12345678901234567890"
    eval(data)
    """
    runner = SecuritySentinelRunner(target_code=sample_code)
    audit = runner.run_audit()

    assert audit["agent_slug"] == "nuuvixx/security-sentinel"
    assert audit["total_findings"] >= 2
    assert audit["verdict"] == "FAILED"
    assert "[REDACTED_KEY]" in audit["redacted_code"]


def test_finops_cost_optimizer_runner_execution():
    runner = FinOpsCostOptimizerRunner()
    res = runner.run_optimization()

    assert res["agent_slug"] == "nuuvixx/finops-cost-optimizer"
    assert res["total_recommendations"] > 0
    assert res["total_monthly_savings_usd"] > 0
    assert res["savings_percentage"] > 0


def test_security_scan_passes_on_real_manifests():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    sec_path = os.path.join(root_dir, "agents", "security_sentinel", "agent.yaml")
    fin_path = os.path.join(root_dir, "agents", "finops_cost_optimizer", "agent.yaml")

    with open(sec_path, "r", encoding="utf-8") as f:
        sec_yaml = yaml.safe_load(f)

    sec_scan = run_full_security_scan(sec_yaml)
    assert sec_scan["passed"] is True

    with open(fin_path, "r", encoding="utf-8") as f:
        fin_yaml = yaml.safe_load(f)

    fin_scan = run_full_security_scan(fin_yaml)
    assert fin_scan["passed"] is True



def test_api_retrieves_real_seeded_agents():
    res = client.get("/api/v1/registry/agents")
    assert res.status_code == 200
    agents = res.json()
    slugs = [a["slug"] for a in agents]

    assert "nuuvixx/security-sentinel" in slugs
    assert "nuuvixx/finops-cost-optimizer" in slugs
