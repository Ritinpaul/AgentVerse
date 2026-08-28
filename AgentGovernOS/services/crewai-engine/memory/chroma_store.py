"""
AgentGovern OS — ChromaDB Persistent Memory Store.

Stores and retrieves decision embeddings for semantic similarity search.
Used by agents to find precedent decisions ("what was decided in similar cases?").
Uses local ChromaDB — no external service required.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Collection names
DECISIONS_COLLECTION = "governance_decisions"
POLICIES_COLLECTION = "active_policies"
EVIDENCE_COLLECTION = "evidence_patterns"


class ChromaStore:
    """
    Persistent ChromaDB memory for AgentGovern agents.

    Stores:
    - Past decision summaries (for precedent lookup)
    - Policy embeddings (for semantic policy matching)
    - Evidence pattern fingerprints (for fraud detection)

    Two-mode operation:
    - With chromadb installed: full vector search
    - Without chromadb: in-memory dict fallback (development)
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str = DECISIONS_COLLECTION,
    ):
        self.collection_name = collection_name
        self.persist_dir = persist_dir or os.path.join(
            os.path.dirname(__file__), "..", ".chroma_data"
        )
        self._client = None
        self._collection = None
        self._fallback: dict[str, dict] = {}  # used when chromadb unavailable
        self._using_fallback = False
        self._init_client

    def _init_client(self) -> None:
        """Initialize ChromaDB client, fall back gracefully if not installed."""
        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB initialized at {self.persist_dir} "
                f"(collection: {self.collection_name}, "
                f"{self._collection.count} entries)"
            )
        except ImportError:
            logger.warning(
                "chromadb not installed — ChromaStore running in dict fallback mode. "
                "Install with: pip install chromadb"
            )
            self._using_fallback = True
        except Exception as e:
            logger.warning(f"ChromaDB init failed: {e} — using fallback mode")
            self._using_fallback = True

    def add(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] = None,
    ) -> bool:
        """
        Add a document to the collection.

        Args:
            doc_id:   Unique ID (e.g., decision UUID)
            text:     Text to embed and store
            metadata: Key-value pairs (must be str/int/float/bool only for ChromaDB)
        Returns:
            True if stored successfully, False otherwise
        """
        safe_meta = self._sanitize_metadata(metadata or {})
        if self._using_fallback:
            self._fallback[doc_id] = {"text": text, "metadata": safe_meta}
            return True
        try:
            self._collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[safe_meta],
            )
            return True
        except Exception as e:
            logger.error(f"ChromaStore.add failed: {e}")
            self._fallback[doc_id] = {"text": text, "metadata": safe_meta}
            return False

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Semantic similarity search.

        Returns:
            List of dicts: [{id, text, metadata, distance}, ...]
        """
        if self._using_fallback:
            return self._fallback_query(query_text, n_results)
        try:
            kwargs: dict = {"query_texts": [query_text], "n_results": min(n_results, self._collection.count)}
            if where:
                kwargs["where"] = where
            results = self._collection.query(**kwargs)
            if not results["ids"] or not results["ids"][0]:
                return []
            return [
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                }
                for i in range(len(results["ids"][0]))
            ]
        except Exception as e:
            logger.error(f"ChromaStore.query failed: {e}")
            return self._fallback_query(query_text, n_results)

    def get(self, doc_id: str) -> dict | None:
        """Get a specific document by ID."""
        if self._using_fallback:
            entry = self._fallback.get(doc_id)
            return entry if entry else None
        try:
            result = self._collection.get(ids=[doc_id], include=["documents", "metadatas"])
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "text": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
            return None
        except Exception as e:
            logger.error(f"ChromaStore.get failed: {e}")
            return None

    def delete(self, doc_id: str) -> bool:
        """Remove a document from the collection."""
        if self._using_fallback:
            self._fallback.pop(doc_id, None)
            return True
        try:
            self._collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"ChromaStore.delete failed: {e}")
            return False

    def count(self) -> int:
        """Return number of stored documents."""
        if self._using_fallback:
            return len(self._fallback)
        try:
            return self._collection.count
        except Exception:
            return 0

    def _fallback_query(self, query_text: str, n_results: int) -> list[dict]:
        """
        Simple keyword-based fallback search when ChromaDB is unavailable.
        Not semantically equivalent — for development only.
        """
        query_words = set(query_text.lower.split)
        scored = []
        for doc_id, entry in self._fallback.items:
            text_words = set(entry["text"].lower.split)
            overlap = len(query_words & text_words)
            if overlap > 0:
                scored.append({
                    "id": doc_id,
                    "text": entry["text"],
                    "metadata": entry["metadata"],
                    "distance": 1.0 - overlap / max(len(query_words), 1),
                })
        scored.sort(key=lambda x: x["distance"])
        return scored[:n_results]

    @staticmethod
    def _sanitize_metadata(meta: dict) -> dict:
        """ChromaDB only accepts str/int/float/bool values."""
        safe = {}
        for k, v in meta.items:
            if isinstance(v, (str, int, float, bool)):
                safe[k] = v
            else:
                safe[k] = str(v)
        return safe

    @property
    def mode(self) -> str:
        return "fallback" if self._using_fallback else "chromadb"
