"""
Agent-to-Agent (A2A) Commerce Router — /api/v1/a2a
Capability discovery directory, autonomous contract negotiation, x402 settlement, provenance logs.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.core.rate_limit import mutation_limit
from app.models.a2a_models import (
    AgentCapabilityAdvertisement, A2AServiceContract, ProvenanceLog
)
from app.services.a2a_engine import (
    advertise_capability, negotiate_service_contract, settle_x402_micropayment
)

router = APIRouter(prefix="/api/v1/a2a", tags=["a2a-commerce"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class AdvertiseRequest(BaseModel):
    agent_slug: str
    capability: str
    endpoint_url: str
    price_per_call_x402: Optional[float] = 0.001


class ContractNegotiateRequest(BaseModel):
    buyer_slug: str
    seller_slug: str
    capability: str


class SettleRequest(BaseModel):
    contract_id: str
    output_data: Optional[str] = "task_execution_result_payload"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/directory/advertise", status_code=201)
@mutation_limit("10/minute")
def advertise(request: Request, req: AdvertiseRequest, db: Session = Depends(get_db)):
    """Agent advertises a service capability to the A2A directory."""
    ad = advertise_capability(
        agent_slug=req.agent_slug,
        capability=req.capability,
        endpoint_url=req.endpoint_url,
        price_per_call_x402=req.price_per_call_x402 or 0.001,
        db=db,
    )
    return {
        "id": ad.id,
        "agent_slug": ad.agent_slug,
        "capability": ad.capability,
        "price_per_call_x402": ad.price_per_call_x402,
        "status": ad.status,
    }


@router.get("/directory")
def search_directory(capability: Optional[str] = None, db: Session = Depends(get_db)):
    """Search advertised agent capabilities in the A2A directory."""
    query = db.query(AgentCapabilityAdvertisement).filter(AgentCapabilityAdvertisement.status == "active")
    if capability:
        query = query.filter(AgentCapabilityAdvertisement.capability.ilike(f"%{capability}%"))
    ads = query.order_by(AgentCapabilityAdvertisement.id.desc()).all()
    return [
        {
            "id": a.id,
            "agent_slug": a.agent_slug,
            "capability": a.capability,
            "endpoint_url": a.endpoint_url,
            "price_per_call_x402": a.price_per_call_x402,
            "advertised_at": a.advertised_at,
        }
        for a in ads
    ]


@router.post("/contracts/negotiate", status_code=201)
@mutation_limit("10/minute")
def negotiate(request: Request, req: ContractNegotiateRequest, db: Session = Depends(get_db)):
    """Buyer agent negotiates an autonomous service contract with seller agent."""
    contract = negotiate_service_contract(
        buyer_slug=req.buyer_slug,
        seller_slug=req.seller_slug,
        capability=req.capability,
        db=db,
    )
    return {
        "contract_id": contract.contract_id,
        "buyer_slug": contract.buyer_slug,
        "seller_slug": contract.seller_slug,
        "capability": contract.capability,
        "agreed_price_usd": contract.agreed_price_usd,
        "status": contract.status,
        "created_at": contract.created_at,
    }


@router.post("/contracts/settle")
@mutation_limit("10/minute")
def settle_payment(request: Request, req: SettleRequest, db: Session = Depends(get_db)):
    """Settle an A2A service contract via x402 micropayment protocol."""
    res = settle_x402_micropayment(
        contract_id=req.contract_id,
        output_data=req.output_data or "task_complete",
        db=db,
    )
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/contracts")
def list_contracts(buyer_slug: Optional[str] = None, seller_slug: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    """List active or completed A2A service contracts."""
    query = db.query(A2AServiceContract)
    if buyer_slug:
        query = query.filter(A2AServiceContract.buyer_slug == buyer_slug)
    if seller_slug:
        query = query.filter(A2AServiceContract.seller_slug == seller_slug)
    if status:
        query = query.filter(A2AServiceContract.status == status)
    contracts = query.order_by(A2AServiceContract.id.desc()).all()
    return [
        {
            "contract_id": c.contract_id,
            "buyer_slug": c.buyer_slug,
            "seller_slug": c.seller_slug,
            "capability": c.capability,
            "agreed_price_usd": c.agreed_price_usd,
            "status": c.status,
            "created_at": c.created_at,
        }
        for c in contracts
    ]


@router.get("/audit-trail")
def audit_trail(contract_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Fetch cryptographic provenance audit logs of A2A commerce activity."""
    query = db.query(ProvenanceLog)
    if contract_id:
        query = query.filter(ProvenanceLog.contract_id == contract_id)
    logs = query.order_by(ProvenanceLog.id.desc()).limit(50).all()
    return [
        {
            "id": l.id,
            "contract_id": l.contract_id,
            "buyer_slug": l.buyer_slug,
            "seller_slug": l.seller_slug,
            "action": l.action,
            "payload_hash": l.payload_hash,
            "timestamp": l.timestamp,
        }
        for l in logs
    ]
