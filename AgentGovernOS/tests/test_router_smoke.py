"""Fast smoke tests for PULSE and SENTINEL routers with mocked DB dependencies."""

# pyright: reportMissingImports=false

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_API = ROOT / "services" / "governance-api"
if str(GOVERNANCE_API) not in sys.path:
    sys.path.insert(0, str(GOVERNANCE_API))

from routers import pulse, sentinel


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalarResult(self._rows)


class _FakeDB:
    def __init__(self, agent=None, policies=None):
        self.agent = agent
        self.policies = policies or []

    async def get(self, _model, _id):
        return self.agent

    async def execute(self, _query):
        return _FakeResult(self.policies)


def _build_pulse_client(monkeypatch, agent):
    app = FastAPI
    app.include_router(pulse.router)

    async def _db:
        yield _FakeDB(agent=agent)

    async def _velocity(_db, _agent_id, days=7):
        return 0.02

    monkeypatch.setattr(pulse, "_get_redis", lambda: None)
    monkeypatch.setattr(pulse, "_calculate_velocity", _velocity)
    app.dependency_overrides[pulse.get_db] = _db
    return TestClient(app)


def _build_sentinel_client(monkeypatch, agent, policies):
    app = FastAPI
    app.include_router(sentinel.router)

    async def _db:
        yield _FakeDB(agent=agent, policies=policies)

    monkeypatch.setattr(sentinel._prophecy, "should_trigger", lambda **_: (False, "not-needed"))
    app.dependency_overrides[sentinel.get_db] = _db
    return TestClient(app)


def test_pulse_get_trust_score(monkeypatch):
    agent_id = uuid4
    agent = SimpleNamespace(
        id=agent_id,
        agent_code="AG-PULSE-1",
        trust_score=Decimal("0.81"),
        tier="T2",
        authority_limit=Decimal("50000.00"),
    )
    client = _build_pulse_client(monkeypatch, agent)

    response = client.get(f"/api/v1/trust/{agent_id}")

    assert response.status_code == 200
    payload = response.json
    assert payload["agent_code"] == "AG-PULSE-1"
    assert payload["tier"] == "T2"


def test_pulse_promotion_eligibility(monkeypatch):
    agent_id = uuid4
    agent = SimpleNamespace(
        id=agent_id,
        agent_code="AG-PULSE-2",
        trust_score=Decimal("0.70"),
        tier="T3",
        authority_limit=Decimal("10000.00"),
        status="active",
        total_decisions=22,
    )
    client = _build_pulse_client(monkeypatch, agent)

    response = client.get(f"/api/v1/trust/{agent_id}/promotion-eligibility")

    assert response.status_code == 200
    payload = response.json
    assert payload["next_tier"] == "T2"
    assert payload["gap"] > 0


def test_sentinel_blocks_on_critical_violation(monkeypatch):
    agent_id = uuid4
    agent = SimpleNamespace(
        id=agent_id,
        agent_code="AG-SENT-1",
        role="hr_bot",
        trust_score=Decimal("0.85"),
        authority_limit=Decimal("10000.00"),
        tier="T3",
        total_decisions=25,
        total_overrides=0,
        total_escalations=1,
    )

    policy = SimpleNamespace(
        policy_code="POL-CRIT-TRUST",
        policy_name="Critical trust minimum",
        applies_to_roles=["*"],
        applies_to_tiers=["*"],
        severity="critical",
        action_on_violation="block",
        rule_definition={"type": "trust_minimum", "min_trust": 0.95},
    )

    client = _build_sentinel_client(monkeypatch, agent, [policy])

    response = client.post(
        "/api/v1/sentinel/evaluate",
        json={
            "agent_id": str(agent_id),
            "action": {"type": "access_pii", "amount": 0},
            "context": {},
        },
    )

    assert response.status_code == 200
    assert response.json["verdict"] == "block"


def test_sentinel_escalates_on_authority_breach(monkeypatch):
    agent_id = uuid4
    agent = SimpleNamespace(
        id=agent_id,
        agent_code="AG-SENT-2",
        role="fi_analyst",
        trust_score=Decimal("0.93"),
        authority_limit=Decimal("10000.00"),
        tier="T3",
        total_decisions=80,
        total_overrides=1,
        total_escalations=2,
    )

    client = _build_sentinel_client(monkeypatch, agent, [])

    response = client.post(
        "/api/v1/sentinel/evaluate",
        json={
            "agent_id": str(agent_id),
            "action": {"type": "approve_purchase", "amount": 250000},
            "context": {},
        },
    )

    assert response.status_code == 200
    assert response.json["verdict"] == "escalate"
