"""
Phase 6 — Agent-to-Agent (A2A) Commerce Models
AgentCapabilityAdvertisement, A2AServiceContract, ProvenanceLog
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.base_class import Base


class AgentCapabilityAdvertisement(Base):
    """Service capabilities advertised by active running agents."""
    __tablename__ = "a2a_capability_advertisements"

    id = Column(Integer, primary_key=True, index=True)
    agent_slug = Column(String, index=True, nullable=False)
    capability = Column(String, index=True, nullable=False)  # e.g., "search:flights", "summarize:doc"
    endpoint_url = Column(String, nullable=False)
    price_per_call_x402 = Column(Float, default=0.001)       # USD / token settlement per call
    status = Column(String, default="active")
    advertised_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class A2AServiceContract(Base):
    """Autonomous service contract between a buyer agent and seller agent."""
    __tablename__ = "a2a_service_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(String, unique=True, index=True, nullable=False)
    buyer_slug = Column(String, index=True, nullable=False)
    seller_slug = Column(String, index=True, nullable=False)
    capability = Column(String, nullable=False)
    agreed_price_usd = Column(Float, nullable=False)

    # Status: quote_requested -> agreed -> executing -> settled / disputed
    status = Column(String, default="agreed")
    x402_tx_hash = Column(String, nullable=True)             # Cryptographic payment receipt
    output_hash = Column(String, nullable=True)              # Cryptographic output verification hash

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    settled_at = Column(DateTime, nullable=True)


class ProvenanceLog(Base):
    """Cryptographic audit trail of all A2A interactions and transactions."""
    __tablename__ = "a2a_provenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(String, index=True, nullable=False)
    buyer_slug = Column(String, nullable=False)
    seller_slug = Column(String, nullable=False)
    action = Column(String, nullable=False)                  # negotiate, execute, x402_settle
    payload_hash = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
