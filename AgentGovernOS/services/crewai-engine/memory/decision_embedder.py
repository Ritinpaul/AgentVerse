"""
AgentGovern OS — Decision Embedder.

Converts governance decisions into searchable embeddings stored in ChromaDB.
Enables agents to find precedent decisions ("how did we resolve similar cases?").
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .chroma_store import DECISIONS_COLLECTION, ChromaStore

logger = logging.getLogger(__name__)


class DecisionEmbedder:
    """
    Embeds governance decisions into ChromaDB for semantic retrieval.

    Each decision is stored as:
    - Text:     Human-readable decision summary (used for embedding)
    - Metadata: Structured data for filtering/retrieval

    Usage:
        embedder = DecisionEmbedder

        # Store a new decision
        embedder.store_decision(
            decision_id="DEC-001",
            dispute_type="short_delivery",
            resolution="partial_credit",
            settlement_amount=54000,
            outcome_summary="Customer claim validated. Partial credit issued...",
            metadata={"customer_tier": "A", "risk_score": 0.32}
        )

        # Find similar past decisions
        similar = embedder.find_similar("invoice dispute short delivery credit note")
    """

    def __init__(self, persist_dir: str | None = None):
        self.store = ChromaStore(
            persist_dir=persist_dir,
            collection_name=DECISIONS_COLLECTION,
        )

    def store_decision(
        self,
        dispute_type: str,
        resolution: str,
        outcome_summary: str,
        settlement_amount: float = 0.0,
        customer_tier: str = "A",
        risk_score: float = 0.0,
        fraud_risk_score: float = 0.0,
        confidence_score: float = 0.0,
        agent_id: str = "",
        dispute_id: str = "",
        decision_id: str | None = None,
        extra_metadata: dict | None = None,
    ) -> str:
        """
        Embed and store a governance decision.

        Returns:
            decision_id (generated if not provided)
        """
        if not decision_id:
            decision_id = str(uuid4)

        # Build rich text for embedding — more context = better similarity search
        embed_text = (
            f"Dispute type: {dispute_type}. "
            f"Resolution: {resolution}. "
            f"Settlement amount: INR {settlement_amount:.2f}. "
            f"Customer tier: {customer_tier}. "
            f"Risk score: {risk_score:.3f}. "
            f"Outcome: {outcome_summary}"
        )

        metadata: dict[str, Any] = {
            "dispute_type": dispute_type,
            "resolution": resolution,
            "settlement_amount": settlement_amount,
            "customer_tier": customer_tier,
            "risk_score": risk_score,
            "fraud_risk_score": fraud_risk_score,
            "confidence_score": confidence_score,
            "agent_id": agent_id,
            "dispute_id": dispute_id,
            "created_at": datetime.now(UTC).isoformat,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        success = self.store.add(
            doc_id=decision_id,
            text=embed_text,
            metadata=metadata,
        )
        if success:
            logger.debug(f"Decision embedded: {decision_id} ({dispute_type} → {resolution})")
        return decision_id

    def find_similar(
        self,
        query: str,
        n_results: int = 5,
        dispute_type_filter: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[dict]:
        """
        Find past decisions most similar to the current query.

        Args:
            query:               Free-text description of current dispute
            n_results:           Number of similar decisions to return
            dispute_type_filter: Only return decisions of this type
            min_confidence:      Filter by minimum confidence score

        Returns:
            List of similar decisions, sorted by relevance
        """
        where = None
        if dispute_type_filter:
            where = {"dispute_type": {"$eq": dispute_type_filter}}

        results = self.store.query(
            query_text=query,
            n_results=n_results,
            where=where,
        )

        # Post-filter by confidence if ChromaDB is in fallback mode
        if min_confidence > 0:
            results = [
                r for r in results
                if r.get("metadata", {}).get("confidence_score", 0) >= min_confidence
            ]

        return results

    def format_precedent_summary(self, similar_decisions: list[dict]) -> str:
        """
        Format similar decisions into a readable precedent summary for agent context.
        """
        if not similar_decisions:
            return "No similar past decisions found in memory.\n"

        lines = [f"PRECEDENT DECISIONS ({len(similar_decisions)} similar cases found)\n{'='*60}"]
        for i, dec in enumerate(similar_decisions, 1):
            meta = dec.get("metadata", {})
            similarity = max(0.0, 1.0 - dec.get("distance", 1.0))
            lines.append(
                f"\n[{i}] Similarity: {similarity:.0%}\n"
                f"    Type:       {meta.get('dispute_type', 'N/A')}\n"
                f"    Resolution: {meta.get('resolution', 'N/A')}\n"
                f"    Amount:     ₹{meta.get('settlement_amount', 0):,.2f}\n"
                f"    Confidence: {meta.get('confidence_score', 0):.0%}\n"
                f"    Summary:    {dec.get('text', '')[:200]}...\n"
            )
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Return memory store statistics."""
        return {
            "total_decisions": self.store.count,
            "storage_mode": self.store.mode,
            "collection": DECISIONS_COLLECTION,
        }


# Module-level singleton (shared across crew runs in the same process)
_default_embedder: DecisionEmbedder | None = None


def get_embedder() -> DecisionEmbedder:
    """Get the module-level decision embedder singleton."""
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = DecisionEmbedder()
    return _default_embedder
