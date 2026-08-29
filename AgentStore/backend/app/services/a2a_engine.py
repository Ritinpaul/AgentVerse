"""
Agent-to-Agent (A2A) Commerce Engine
Capability advertising, autonomous contract negotiation, x402 micropayment settlement, provenance logging.
"""
from __future__ import annotations
import uuid
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.a2a_models import (
    AgentCapabilityAdvertisement, A2AServiceContract, ProvenanceLog
)


def advertise_capability(
    agent_slug: str, capability: str, endpoint_url: str, price_per_call_x402: float, db: Session
) -> AgentCapabilityAdvertisement:
    ad = AgentCapabilityAdvertisement(
        agent_slug=agent_slug,
        capability=capability,
        endpoint_url=endpoint_url,
        price_per_call_x402=price_per_call_x402,
        status="active",
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


def negotiate_service_contract(
    buyer_slug: str, seller_slug: str, capability: str, db: Session
) -> A2AServiceContract:
    ad = db.query(AgentCapabilityAdvertisement).filter(
        AgentCapabilityAdvertisement.agent_slug == seller_slug,
        AgentCapabilityAdvertisement.capability == capability,
    ).first()

    price = ad.price_per_call_x402 if ad else 0.001
    contract_id = f"ct_{uuid.uuid4().hex[:12]}"

    contract = A2AServiceContract(
        contract_id=contract_id,
        buyer_slug=buyer_slug,
        seller_slug=seller_slug,
        capability=capability,
        agreed_price_usd=price,
        status="agreed",
    )
    db.add(contract)

    # Log provenance event
    payload_raw = f"{buyer_slug}:{seller_slug}:{capability}:{price}"
    payload_hash = f"sha256:{hashlib.sha256(payload_raw.encode()).hexdigest()[:16]}"

    log = ProvenanceLog(
        contract_id=contract_id,
        buyer_slug=buyer_slug,
        seller_slug=seller_slug,
        action="negotiate_contract",
        payload_hash=payload_hash,
    )
    db.add(log)
    db.commit()
    db.refresh(contract)

    return contract


def settle_x402_micropayment(
    contract_id: str, output_data: str, db: Session
) -> dict:
    contract = db.query(A2AServiceContract).filter(A2AServiceContract.contract_id == contract_id).first()
    if not contract:
        return {"error": "Contract not found"}

    out_hash = f"sha256:{hashlib.sha256(output_data.encode()).hexdigest()[:16]}"
    tx_hash = f"x402_tx_{uuid.uuid4().hex[:16]}"

    contract.status = "settled"
    contract.output_hash = out_hash
    contract.x402_tx_hash = tx_hash
    contract.settled_at = datetime.now(timezone.utc)

    # Provenance log
    log = ProvenanceLog(
        contract_id=contract_id,
        buyer_slug=contract.buyer_slug,
        seller_slug=contract.seller_slug,
        action="x402_settle",
        payload_hash=tx_hash,
    )
    db.add(log)
    db.commit()

    return {
        "contract_id": contract_id,
        "buyer_slug": contract.buyer_slug,
        "seller_slug": contract.seller_slug,
        "agreed_price_usd": contract.agreed_price_usd,
        "status": "settled",
        "x402_tx_hash": tx_hash,
        "output_hash": out_hash,
    }
