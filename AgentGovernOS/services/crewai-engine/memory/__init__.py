"""
AgentGovern OS — Memory Package.

Provides persistent semantic memory for agent decision precedent lookup.
"""

from .chroma_store import (
    DECISIONS_COLLECTION,
    EVIDENCE_COLLECTION,
    POLICIES_COLLECTION,
    ChromaStore,
)
from .decision_embedder import DecisionEmbedder, get_embedder

__all__ = [
    "DECISIONS_COLLECTION",
    "EVIDENCE_COLLECTION",
    "POLICIES_COLLECTION",
    "ChromaStore",
    "DecisionEmbedder",
    "get_embedder",
]
