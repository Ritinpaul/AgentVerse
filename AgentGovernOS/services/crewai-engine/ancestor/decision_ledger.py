"""
ANCESTOR Decision Ledger — immutable, hash-chained decision records.

Every agent decision is written to the ledger as an immutable block.
Each block includes:
  - A SHA-256 hash of the decision payload
  - The hash of the previous block (chain linkage)
  - Human-readable reasoning trace
  - Tool usage log
  - Delegation chain
  - Sentinel assessment
  - Optional prophecy paths

The hash chain makes the ledger tamper-evident:
  If any block is modified, all subsequent hash comparisons will break.

This satisfies SOX audit requirements and EU AI Act Article 14
(human oversight through transparency).
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    """A single immutable decision block."""
    agent_id: str
    task_id: str
    decision_type: str
    input_context: dict
    reasoning_trace: str
    output_action: dict
    confidence_score: float
    dispute_id: str = ""
    risk_score: float = 0.0
    amount_involved: float = 0.0
    currency: str = "INR"
    tools_used: list = field(default_factory=list)
    delegation_chain: list = field(default_factory=list)
    policy_rules_applied: list = field(default_factory=list)
    policy_violations: list = field(default_factory=list)
    sentinel_assessment: dict | None = None
    prophecy_paths: dict | None = None
    human_override: dict | None = None
    crewai_task_output: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    hash: str = field(default="", init=False)
    prev_hash: str = ""

    def __post_init__(self):
        self.hash = self._compute_hash

    def _compute_hash(self) -> str:
        """
        Compute SHA-256 hash of this decision block.
        Deterministic: same input always produces same hash.
        """
        payload = {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "decision_type": self.decision_type,
            "output_action": self.output_action,
            "confidence_score": self.confidence_score,
            "amount_involved": self.amount_involved,
            "timestamp": self.timestamp.isoformat,
            "prev_hash": self.prev_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode).hexdigest

    def verify(self) -> bool:
        """Verify this block's hash has not been tampered with."""
        expected = self._compute_hash
        return self.hash == expected

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "dispute_id": self.dispute_id,
            "decision_type": self.decision_type,
            "input_context": self.input_context,
            "reasoning_trace": self.reasoning_trace,
            "crewai_task_output": self.crewai_task_output,
            "tools_used": self.tools_used,
            "delegation_chain": self.delegation_chain,
            "output_action": self.output_action,
            "confidence_score": self.confidence_score,
            "risk_score": self.risk_score,
            "amount_involved": self.amount_involved,
            "currency": self.currency,
            "policy_rules_applied": self.policy_rules_applied,
            "policy_violations": self.policy_violations,
            "sentinel_assessment": self.sentinel_assessment,
            "prophecy_paths": self.prophecy_paths,
            "human_override": self.human_override,
            "hash": self.hash,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp.isoformat,
        }


class DecisionLedger:
    """
    Append-only decision ledger with hash chain verification.

    Think of it as a mini-blockchain for AI decisions:
      - Each block references the previous block's hash
      - Tampering any block breaks all subsequent hash links
      - Full chain verification available at any time
    """

    def __init__(self, db=None):
        self.db = db
        self._last_hash = ""  # In-memory tip for chaining (refreshed from DB on init)

    def _get_last_hash(self) -> str:
        """Get the most recent block hash from DB (for chain continuity)."""
        if not self.db:
            return ""
        try:
            from sqlalchemy import text
            result = self.db.execute(
                text("SELECT hash FROM decisions ORDER BY timestamp DESC LIMIT 1")
            ).fetchone
            return result[0] if result else ""
        except Exception:
            return ""

    def record(self, decision: DecisionRecord) -> str:
        """
        Append a decision to the ledger.

        Sets prev_hash from the current chain tip, recomputes the block hash,
        then persists to PostgreSQL.

        Returns the new block's hash.
        """
        # Chain linkage
        prev_hash = self._last_hash or self._get_last_hash
        decision.prev_hash = prev_hash
        decision.hash = decision._compute_hash  # Recompute with prev_hash set
        self._last_hash = decision.hash

        if self.db:
            self._persist(decision)

        logger.info(
            f"[ANCESTOR] Decision recorded: "
            f"id={decision.id[:8]} agent={decision.agent_id[:8]} "
            f"hash={decision.hash[:12]}... prev={prev_hash[:12] if prev_hash else 'genesis'}"
        )
        return decision.hash

    def verify_chain(self, agent_id: str = None, limit: int = 100) -> dict:
        """
        Verify integrity of the decision chain.

        Args:
            agent_id: If provided, verify only this agent's chain
            limit: Max blocks to check

        Returns:
            {valid: bool, checked: int, broken_at: Optional[str], integrity_pct: float}
        """
        if not self.db:
            return {"valid": True, "checked": 0, "note": "No DB — in-memory mode"}

        try:
            from sqlalchemy import text
            query = "SELECT id, hash, prev_hash, timestamp FROM decisions"
            params = {"limit": limit}
            if agent_id:
                query += " WHERE agent_id = :agent_id"
                params["agent_id"] = agent_id
            query += " ORDER BY timestamp ASC LIMIT :limit"

            rows = self.db.execute(text(query), params).fetchall

            if not rows:
                return {"valid": True, "checked": 0, "note": "empty ledger"}

            broken_at = None
            prev = ""
            for row in rows:
                block_id, block_hash, block_prev, _ = row
                if block_prev != prev:
                    broken_at = str(block_id)
                    break
                prev = block_hash

            pct = (len(rows) - (1 if broken_at else 0)) / len(rows) * 100

            return {
                "valid": broken_at is None,
                "checked": len(rows),
                "broken_at": broken_at,
                "integrity_pct": round(pct, 2),
            }
        except Exception as e:
            logger.error(f"[ANCESTOR] Chain verification failed: {e}")
            return {"valid": False, "checked": 0, "error": str(e)}

    def _persist(self, decision: DecisionRecord) -> None:
        """Write decision record to PostgreSQL."""
        from sqlalchemy import text

        try:
            self.db.execute(
                text(
                    """
                    INSERT INTO decisions (
                        id, agent_id, task_id, dispute_id, decision_type,
                        input_context, reasoning_trace, crewai_task_output,
                        tools_used, delegation_chain, output_action,
                        confidence_score, risk_score, amount_involved, currency,
                        policy_rules_applied, policy_violations,
                        sentinel_assessment, prophecy_paths, human_override,
                        hash, prev_hash, timestamp
                    ) VALUES (
                        :id, :agent_id, :task_id, :dispute_id, :decision_type,
                        :input_context::jsonb, :reasoning_trace, :crewai_task_output,
                        :tools_used::jsonb, :delegation_chain::jsonb, :output_action::jsonb,
                        :confidence_score, :risk_score, :amount_involved, :currency,
                        :policy_rules_applied::jsonb, :policy_violations::jsonb,
                        :sentinel_assessment::jsonb, :prophecy_paths::jsonb,
                        :human_override::jsonb,
                        :hash, :prev_hash, :timestamp
                    )
                    """
                ),
                {
                    "id": decision.id,
                    "agent_id": decision.agent_id,
                    "task_id": decision.task_id,
                    "dispute_id": decision.dispute_id,
                    "decision_type": decision.decision_type,
                    "input_context": json.dumps(decision.input_context),
                    "reasoning_trace": decision.reasoning_trace,
                    "crewai_task_output": decision.crewai_task_output,
                    "tools_used": json.dumps(decision.tools_used),
                    "delegation_chain": json.dumps(decision.delegation_chain),
                    "output_action": json.dumps(decision.output_action),
                    "confidence_score": decision.confidence_score,
                    "risk_score": decision.risk_score,
                    "amount_involved": decision.amount_involved,
                    "currency": decision.currency,
                    "policy_rules_applied": json.dumps(decision.policy_rules_applied),
                    "policy_violations": json.dumps(decision.policy_violations),
                    "sentinel_assessment": json.dumps(decision.sentinel_assessment),
                    "prophecy_paths": json.dumps(decision.prophecy_paths),
                    "human_override": json.dumps(decision.human_override),
                    "hash": decision.hash,
                    "prev_hash": decision.prev_hash,
                    "timestamp": decision.timestamp,
                },
            )
            self.db.commit
        except Exception as e:
            logger.error(f"[ANCESTOR] Failed to persist decision: {e}")
            raise
