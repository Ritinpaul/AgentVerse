"""
Phase 6 Tests — Agent-to-Agent Commerce & x402 Settlement
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base

from app.services.a2a_engine import (
    advertise_capability, negotiate_service_contract, settle_x402_micropayment
)
from app.models.a2a_models import ProvenanceLog


@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_advertise_capability(db):
    ad = advertise_capability(
        agent_slug="acme/flight-finder",
        capability="search:flights",
        endpoint_url="https://api.acme.ai/a2a/flights",
        price_per_call_x402=0.002,
        db=db,
    )
    assert ad.id is not None
    assert ad.capability == "search:flights"
    assert ad.price_per_call_x402 == 0.002


def test_negotiate_service_contract(db):
    advertise_capability("acme/flight-finder", "search:flights", "https://api.acme.ai/a2a", 0.002, db)

    contract = negotiate_service_contract(
        buyer_slug="travel/trip-planner",
        seller_slug="acme/flight-finder",
        capability="search:flights",
        db=db,
    )
    assert contract.contract_id.startswith("ct_")
    assert contract.agreed_price_usd == 0.002
    assert contract.status == "agreed"

    # Verify provenance log entry created
    log = db.query(ProvenanceLog).filter(ProvenanceLog.contract_id == contract.contract_id).first()
    assert log is not None
    assert log.action == "negotiate_contract"


def test_settle_x402_micropayment(db):
    advertise_capability("acme/flight-finder", "search:flights", "https://api.acme.ai/a2a", 0.002, db)
    contract = negotiate_service_contract("travel/trip-planner", "acme/flight-finder", "search:flights", db)

    res = settle_x402_micropayment(contract.contract_id, "flight_results_payload_json", db)
    assert res["status"] == "settled"
    assert res["x402_tx_hash"].startswith("x402_tx_")
    assert res["output_hash"].startswith("sha256:")

    # Verify second provenance entry logged
    logs = db.query(ProvenanceLog).filter(ProvenanceLog.contract_id == contract.contract_id).all()
    assert len(logs) == 2
    assert logs[1].action == "x402_settle"
