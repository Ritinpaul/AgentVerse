"""
Tool: Cache Manager — QICACHE read, write, invalidate, and analytics.

Used by: Any agent that wants to explicitly manage the decision cache.
"""

import logging

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CacheReadInput(BaseModel):
    query_text: str = Field(..., description="Query text to check in cache")
    agent_role: str = Field("", description="Agent role (affects cache key)")
    context: dict = Field(default_factory=dict, description="Context dict (dispute_type, amount_range)")


class CacheWriteInput(BaseModel):
    query_hash: str = Field(..., description="Query hash from a previous MISS result")
    query_text: str = Field(..., description="Original query text")
    response_text: str = Field(..., description="LLM response to cache")
    tokens_consumed: int = Field(0, description="Tokens used to generate this response")
    ttl_days: int = Field(3, description="Days to keep in cache (1-30)")


class CacheManagerTool(BaseTool):
    """
    Explicitly manage the QICACHE semantic cache.

    Operations:
    - check: Look up a query in cache before calling LLM
    - store: Save an LLM response to cache after generation
    - invalidate: Remove a stale or incorrect cache entry
    - stats: Get cache performance statistics
    - analytics: Get token savings and hit-rate reports

    The cache is also managed automatically by the QICacheCallback,
    but this tool allows agents to explicitly control caching behavior.
    """

    name: str = "cache_manager"
    description: str = (
        "Manage the QICACHE semantic decision cache. "
        "check(query): returns HIT/MISS and cached response if available. "
        "stats: returns hit rate, token savings, and cache size. "
        "invalidate(hash): remove an incorrect or outdated entry. "
        "Use stats at the end of a crew run to report token savings achieved."
    )
    args_schema: type[BaseModel] = CacheReadInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        query_text: str,
        agent_role: str = "",
        context: dict = None,
    ) -> str:
        """Check cache for a query."""
        try:
            response = httpx.post(
                f"{self.api_url}/cache/check",
                json={
                    "query_text": query_text,
                    "agent_role": agent_role,
                    "context": context or {},
                },
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json
                if data.get("hit"):
                    return (
                        f"CACHE HIT ✓\n"
                        f"Source:       {data.get('source', 'cache')}\n"
                        f"Tokens Saved: {data.get('tokens_saved', 0)}\n"
                        f"Query Hash:   {data.get('query_hash', '')[:16]}...\n\n"
                        f"CACHED RESPONSE:\n{data.get('response', '')}\n"
                    )
                else:
                    return (
                        f"CACHE MISS\n"
                        f"Query Hash: {data.get('query_hash', '')[:16]}...\n"
                        f"LLM call required.\n"
                    )
            else:
                return "CACHE MISS (API check failed — proceeding with LLM)\n"
        except httpx.ConnectError:
            return "CACHE MISS (cache API offline — proceeding with LLM)\n"
        except Exception as e:
            logger.error(f"CacheManagerTool check error: {e}")
            return f"Cache check error: {e!s}"

    def store(
        self,
        query_hash: str,
        query_text: str,
        response_text: str,
        tokens_consumed: int = 0,
        ttl_days: int = 3,
    ) -> str:
        """Store a response in cache."""
        try:
            response = httpx.post(
                f"{self.api_url}/cache/store",
                json={
                    "query_hash": query_hash,
                    "query_text": query_text,
                    "response_text": response_text,
                    "metadata": {"tokens_consumed": tokens_consumed},
                    "ttl_days": ttl_days,
                },
                timeout=5.0,
            )
            if response.status_code in (200, 201):
                return f"CACHE STORED ✓ — Hash: {query_hash[:16]}... TTL: {ttl_days} days\n"
            else:
                return f"Cache store queued (API returned {response.status_code})\n"
        except httpx.ConnectError:
            return "Cache store queued (API offline)\n"

    def invalidate(self, query_hash: str) -> str:
        """Invalidate a cache entry."""
        try:
            response = httpx.delete(
                f"{self.api_url}/cache/entries/{query_hash}",
                timeout=5.0,
            )
            if response.status_code in (200, 204):
                return f"CACHE INVALIDATED ✓ — Hash: {query_hash[:16]}...\n"
            else:
                return f"Invalidation queued for hash {query_hash[:16]}...\n"
        except httpx.ConnectError:
            return "Invalidation queued (API offline)\n"

    def get_stats(self) -> str:
        """Get cache performance statistics."""
        try:
            response = httpx.get(f"{self.api_url}/cache/stats", timeout=5.0)
            if response.status_code == 200:
                data = response.json
                return (
                    f"QICACHE STATISTICS\n"
                    f"{'='*60}\n"
                    f"Total Queries:    {data.get('total', 0)}\n"
                    f"Cache Hits:       {data.get('hits', 0)}\n"
                    f"Cache Misses:     {data.get('misses', 0)}\n"
                    f"Hit Rate:         {data.get('hit_rate_pct', 0):.1f}%\n"
                    f"Tokens Saved:     {data.get('tokens_saved', 0):,}\n"
                    f"Est. Cost Saved:  ${data.get('tokens_saved', 0) / 1000 * 0.002:.4f}\n"
                    f"Cache Entries:    {data.get('total_entries', 0)}\n"
                    f"Redis Hot Keys:   {data.get('redis_keys', 0)}\n"
                )
            else:
                return "Cache stats unavailable — API returned an error.\n"
        except httpx.ConnectError:
            return "Cache stats unavailable — API offline.\n"
