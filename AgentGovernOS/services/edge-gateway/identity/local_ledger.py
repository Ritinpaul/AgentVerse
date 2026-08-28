"""
Local Ledger — edge-side decision ledger with batch sync to control plane.

Every authorization decision made by the Edge Gateway is recorded locally.
Entries are batch-synced to the Control Plane (ANCESTOR master chain) every 30s
or immediately on shutdown.

Offline resilience:
  - If sync fails, entries stay in the local buffer
  - On reconnect, the full backlog is flushed
  - Local hashes are verified by the control plane on receipt
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class LocalDecision:
    agent_id: str
    action_type: str
    resource: str
    amount: float
    environment: str
    verdict: str
    reason: str
    passport_jti: str
    gateway_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    hash: str = field(default="", init=False)
    synced: bool = False

    def __post_init__(self):
        self.hash = self._compute_hash

    def _compute_hash(self) -> str:
        payload = {
            "id": self.id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "verdict": self.verdict,
            "amount": self.amount,
            "environment": self.environment,
            "timestamp": self.timestamp.isoformat,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode
        ).hexdigest

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "resource": self.resource,
            "amount": self.amount,
            "environment": self.environment,
            "verdict": self.verdict,
            "reason": self.reason,
            "passport_jti": self.passport_jti,
            "gateway_id": self.gateway_id,
            "hash": self.hash,
            "timestamp": self.timestamp.isoformat,
            "synced": self.synced,
        }


class LocalLedger:
    """Append-only local decision buffer with batch-sync capability."""

    def __init__(self, gateway_id: str):
        self.gateway_id = gateway_id
        self._entries: list[LocalDecision] = []
        self.last_decision_id: str = ""

    def record_decision(
        self,
        agent_id: str,
        action_type: str,
        resource: str,
        amount: float,
        environment: str,
        verdict: str,
        reason: str,
        passport_jti: str,
    ) -> str:
        """Record a decision. Returns the decision ID."""
        entry = LocalDecision(
            agent_id=agent_id,
            action_type=action_type,
            resource=resource,
            amount=amount,
            environment=environment,
            verdict=verdict,
            reason=reason,
            passport_jti=passport_jti,
            gateway_id=self.gateway_id,
        )
        self._entries.append(entry)
        self.last_decision_id = entry.id
        logger.debug(f"[LOCAL-LEDGER] Recorded: {entry.id[:8]} verdict={verdict}")
        return entry.id

    def get_unsynced(self) -> list[LocalDecision]:
        """Return all entries not yet synced to the control plane."""
        return [e for e in self._entries if not e.synced]

    def mark_synced(self, ids: list[str]) -> int:
        """Mark entries as synced after successful upload."""
        synced_set = set(ids)
        count = 0
        for e in self._entries:
            if e.id in synced_set:
                e.synced = True
                count += 1
        return count

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def unsynced_count(self) -> int:
        return len(self.get_unsynced)
