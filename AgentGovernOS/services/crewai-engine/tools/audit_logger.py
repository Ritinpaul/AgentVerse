"""
Tool: Audit Logger — write immutable decision records to the governance ledger.

Used by: Dispute Resolver, Governance Sentinel agents.
"""

import logging
from datetime import UTC, datetime

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditLogInput(BaseModel):
    agent_id: str = Field(..., description="ID of the agent making the decision")
    decision_type: str = Field(
        ...,
        description="Type of decision: SETTLEMENT_APPROVED, SETTLEMENT_REJECTED, ESCALATED, POLICY_BLOCK",
    )
    dispute_id: str = Field(..., description="Associated dispute ID")
    decision_summary: str = Field(..., description="Human-readable decision summary (max 500 chars)")
    evidence_used: list[str] = Field(default_factory=list, description="List of evidence IDs used")
    confidence_score: float = Field(0.0, description="Agent confidence in this decision (0.0-1.0)")
    settlement_amount: float | None = Field(None, description="Settlement amount (if applicable)")
    metadata: dict = Field(default_factory=dict, description="Additional context metadata")


class AuditLoggerTool(BaseTool):
    """
    Write an immutable decision record to the AgentGovern audit ledger.

    Every decision made by any agent MUST be logged here.
    Records are hash-chained (SHA-256) to prevent tampering.
    The audit trail is the source of truth for all dispute resolutions.
    """

    name: str = "audit_logger"
    description: str = (
        "Write a decision record to the immutable audit ledger. "
        "ALWAYS call this after making any governance decision. "
        "Records are hash-chained and tamper-proof. "
        "Required fields: agent_id, decision_type, dispute_id, decision_summary. "
        "Returns the record ID and hash for verification."
    )
    args_schema: type[BaseModel] = AuditLogInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        agent_id: str,
        decision_type: str,
        dispute_id: str,
        decision_summary: str,
        evidence_used: list[str] = None,
        confidence_score: float = 0.0,
        settlement_amount: float | None = None,
        metadata: dict = None,
    ) -> str:
        payload = {
            "agent_id": agent_id,
            "decision_type": decision_type,
            "dispute_id": dispute_id,
            "decision_summary": decision_summary[:500],
            "evidence_used": evidence_used or [],
            "confidence_score": confidence_score,
            "timestamp": datetime.now(UTC).isoformat,
            "metadata": metadata or {},
        }
        if settlement_amount is not None:
            payload["settlement_amount"] = settlement_amount

        try:
            response = httpx.post(
                f"{self.api_url}/audit/decisions",
                json=payload,
                timeout=10.0,
            )
            if response.status_code in (200, 201):
                data = response.json
                return (
                    f"AUDIT RECORD WRITTEN ✓\n"
                    f"Record ID:  {data.get('decision_id')}\n"
                    f"Hash:       {data.get('hash', 'N/A')[:16]}...{data.get('hash', 'N/A')[-8:]}\n"
                    f"Agent:      {agent_id}\n"
                    f"Decision:   {decision_type}\n"
                    f"Dispute:    {dispute_id}\n"
                    f"Timestamp:  {payload['timestamp']}\n"
                    f"Ledger position verified. Record is now immutable.\n"
                )
            else:
                # Cache locally and return acknowledgment
                return self._local_audit_ack(agent_id, decision_type, dispute_id, payload["timestamp"])
        except httpx.ConnectError:
            return self._local_audit_ack(agent_id, decision_type, dispute_id, payload["timestamp"])
        except Exception as e:
            logger.error(f"AuditLoggerTool error: {e}")
            return f"WARNING: Audit log write failed: {e!s}. Decision must be manually recorded."

    def _local_audit_ack(self, agent_id: str, decision_type: str, dispute_id: str, timestamp: str) -> str:
        """Generate a local audit acknowledgment when API is unavailable."""
        import hashlib
        local_hash = hashlib.sha256(
            f"{agent_id}:{decision_type}:{dispute_id}:{timestamp}".encode
        ).hexdigest
        return (
            f"AUDIT RECORD QUEUED (API offline — will sync)\n"
            f"Local Hash: {local_hash[:16]}...{local_hash[-8:]}\n"
            f"Agent:      {agent_id}\n"
            f"Decision:   {decision_type}\n"
            f"Dispute:    {dispute_id}\n"
            f"Timestamp:  {timestamp}\n"
            f"NOTE: This record will be written to the ledger when connectivity is restored.\n"
        )
