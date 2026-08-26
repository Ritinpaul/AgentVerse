"""
AgentOS Python SDK — A2A Commerce Client.

Bridge 6 (A2A Commerce via AgentStore):
Enables agents to discover, negotiate contracts with, and settle payments to
other agents via the AgentStore A2A Commerce API.

Features:
  - Capability-based agent discovery (GET /a2a/directory)
  - Contract negotiation (POST /a2a/contracts/negotiate)
  - x402 micropayment settlement with SHA-256 provenance hashing
  - Full audit trail in AgentStore's immutable A2A ledger

Usage:
    from nuuvixx.a2a import A2AClient

    a2a = A2AClient(buyer_slug="nuuvixx/orchestrator-agent")

    # Discover and hire a capable agent
    contract = a2a.hire_agent("search:flights")

    # ... buyer calls seller to perform the work ...
    seller_output = call_seller_api(contract)

    # Settle the contract and record provenance
    settlement = a2a.settle_contract(
        contract_id=contract["contract_id"],
        output_data=seller_output
    )
    print(f"Settled! Tx hash: {settlement['tx_hash']}")
"""

import httpx
import os
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from pathlib import Path

try:
    for _parent in Path(__file__).resolve().parents:
        _env = _parent / ".env"
        if _env.exists():
            load_dotenv(dotenv_path=_env, override=False)
            break
except Exception:
    pass

logger = logging.getLogger(__name__)

AGENTSTORE_URL  = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
NUUVIXX_API_KEY = os.getenv("NUUVIXX_API_KEY", "")


def _store_headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if NUUVIXX_API_KEY:
        h["X-API-Key"] = NUUVIXX_API_KEY
    return h


class A2AClient:
    """
    Agent-to-Agent Commerce Client.

    Provides a simple Pythonic API for agents to discover, hire, and
    settle with other agents in the Nuuvixx AgentStore marketplace.
    """

    def __init__(
        self,
        buyer_slug: str,
        agentstore_url: Optional[str] = None,
        timeout: float = 10.0,
    ):
        """
        Args:
            buyer_slug:      The AgentStore slug of the calling (buyer) agent.
                             e.g. "nuuvixx/orchestrator-agent"
            agentstore_url:  Override the AgentStore URL (defaults to env var).
            timeout:         HTTP request timeout in seconds.
        """
        self.buyer_slug   = buyer_slug
        self.base_url     = agentstore_url or AGENTSTORE_URL
        self.timeout      = timeout
        self._http        = httpx.Client(base_url=self.base_url, timeout=timeout)

    # ── Discovery ─────────────────────────────────────────────────────────────

    def discover(self, capability: str, min_trust_score: int = 70) -> List[Dict[str, Any]]:
        """
        Discover agents in the AgentStore directory that offer a given capability.

        Args:
            capability:      The capability to search for (e.g. "search:flights",
                             "nlp:summarize", "data:scrape").
            min_trust_score: Filter out agents below this trust score.

        Returns:
            List of seller agent dicts: [{agent_slug, capabilities, trust_score, price_per_call_usd}, ...]

        Example:
            sellers = a2a.discover("search:flights", min_trust_score=80)
        """
        try:
            r = self._http.get(
                "/api/v1/a2a/directory",
                headers=_store_headers(),
                params={"capability": capability, "min_trust_score": min_trust_score},
            )
            r.raise_for_status()
            sellers = r.json()
            if isinstance(sellers, list):
                return sellers
            return sellers.get("agents", sellers.get("results", []))
        except httpx.HTTPStatusError as e:
            logger.warning(f"[A2AClient] Directory lookup failed {e.response.status_code}: {e.response.text}")
            return []
        except httpx.RequestError as e:
            logger.error(f"[A2AClient] Cannot reach AgentStore: {e}")
            return []

    # ── Negotiation ───────────────────────────────────────────────────────────

    def negotiate(
        self,
        seller_slug: str,
        capability: str,
        terms: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Negotiate a service contract with a seller agent.

        Args:
            seller_slug: The AgentStore slug of the seller agent.
            capability:  The capability being contracted.
            terms:       Optional additional contract terms (e.g. max_price_usd, sla_ms).

        Returns:
            Contract dict: {contract_id, buyer_slug, seller_slug, capability,
                            price_per_call_usd, x402_payment_pointer, status}

        Raises:
            RuntimeError: if negotiation fails.
        """
        body = {
            "buyer_slug": self.buyer_slug,
            "seller_slug": seller_slug,
            "capability": capability,
            **(terms or {}),
        }
        try:
            r = self._http.post(
                "/api/v1/a2a/contracts/negotiate",
                json=body,
                headers=_store_headers(),
            )
            r.raise_for_status()
            contract = r.json()
            logger.info(
                f"[A2AClient] Contract negotiated: {contract.get('contract_id')} "
                f"({self.buyer_slug} → {seller_slug} for '{capability}')"
            )
            return contract
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"A2A contract negotiation failed {e.response.status_code}: {e.response.text}"
            )

    # ── Convenience: Hire = Discover + Negotiate ───────────────────────────────

    def hire_agent(
        self,
        capability: str,
        min_trust_score: int = 70,
        preferred_seller: Optional[str] = None,
        terms: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Discover the best available agent for a capability and negotiate a contract.

        This is the primary A2A entry point for agents that want to delegate work.

        Args:
            capability:       The capability to hire for (e.g. "search:flights").
            min_trust_score:  Minimum trust score for seller selection.
            preferred_seller: If set, try this seller slug first before directory search.
            terms:            Optional contract terms override.

        Returns:
            Contract dict ready for use.

        Raises:
            ValueError: if no suitable agent is found.
            RuntimeError: if negotiation fails.

        Example:
            contract = a2a.hire_agent("nlp:summarize", min_trust_score=80)
            # ... call seller ...
            settlement = a2a.settle_contract(contract["contract_id"], output)
        """
        seller_slug = preferred_seller

        if not seller_slug:
            sellers = self.discover(capability, min_trust_score=min_trust_score)
            if not sellers:
                raise ValueError(
                    f"No agents found in AgentStore for capability '{capability}' "
                    f"with trust_score >= {min_trust_score}. "
                    f"Check: {self.base_url}/api/v1/a2a/directory?capability={capability}"
                )
            # Select highest trust score
            sellers_sorted = sorted(
                sellers,
                key=lambda s: s.get("trust_score", 0),
                reverse=True,
            )
            seller_slug = sellers_sorted[0]["agent_slug"]
            logger.info(
                f"[A2AClient] Selected seller '{seller_slug}' "
                f"(trust={sellers_sorted[0].get('trust_score', '?')}) "
                f"for capability '{capability}'"
            )

        return self.negotiate(seller_slug, capability, terms=terms)

    # ── Settlement ────────────────────────────────────────────────────────────

    def settle_contract(
        self,
        contract_id: str,
        output_data: Any,
        outcome: str = "success",
    ) -> Dict[str, Any]:
        """
        Settle an A2A contract after the seller has delivered its output.

        Records the transaction in AgentStore's immutable audit trail with:
          - SHA-256 payload hash (provenance)
          - x402 micropayment tx hash (if applicable)
          - Output data reference

        Args:
            contract_id: The contract ID from negotiate() or hire_agent().
            output_data: The seller's output (serialized as JSON).
            outcome:     "success" | "failed" | "partial"

        Returns:
            Settlement dict: {settlement_id, tx_hash, amount_usd, audit_trail_id}

        Raises:
            RuntimeError: if settlement fails.
        """
        import json, hashlib

        # Serialize output for provenance hashing
        if not isinstance(output_data, str):
            output_str = json.dumps(output_data, default=str)
        else:
            output_str = output_data

        output_hash = hashlib.sha256(output_str.encode()).hexdigest()

        body = {
            "contract_id": contract_id,
            "output_data": output_str,
            "output_hash": output_hash,
            "outcome": outcome,
            "buyer_slug": self.buyer_slug,
        }

        try:
            r = self._http.post(
                "/api/v1/a2a/contracts/settle",
                json=body,
                headers=_store_headers(),
            )
            r.raise_for_status()
            settlement = r.json()
            logger.info(
                f"[A2AClient] Contract {contract_id} settled: "
                f"tx_hash={str(settlement.get('tx_hash', ''))[:16]}... "
                f"amount=${settlement.get('amount_usd', 0):.4f}"
            )
            return settlement
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"A2A settlement failed {e.response.status_code}: {e.response.text}"
            )

    # ── Utility ───────────────────────────────────────────────────────────────

    def list_active_contracts(self) -> List[Dict[str, Any]]:
        """Returns all active contracts where this agent is the buyer."""
        try:
            r = self._http.get(
                f"/api/v1/a2a/contracts",
                headers=_store_headers(),
                params={"buyer_slug": self.buyer_slug, "status": "active"},
            )
            r.raise_for_status()
            result = r.json()
            return result if isinstance(result, list) else result.get("contracts", [])
        except Exception as e:
            logger.warning(f"[A2AClient] list_active_contracts failed: {e}")
            return []

    def get_audit_trail(self, contract_id: str) -> Dict[str, Any]:
        """Returns the full cryptographic audit trail for a contract."""
        try:
            r = self._http.get(
                f"/api/v1/a2a/audit/{contract_id}",
                headers=_store_headers(),
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"[A2AClient] get_audit_trail failed: {e}")
            return {}

    def close(self):
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── Module-level convenience functions ────────────────────────────────────────

def hire_agent(buyer_slug: str, capability: str, min_trust_score: int = 70) -> Dict[str, Any]:
    """
    Convenience function: Discover + negotiate in one call.

    Example:
        from nuuvixx.a2a import hire_agent, settle_contract

        contract = hire_agent("nuuvixx/my-agent", "search:flights")
        # ... do work ...
        settlement = settle_contract(contract["contract_id"], result, buyer_slug="nuuvixx/my-agent")
    """
    with A2AClient(buyer_slug=buyer_slug) as client:
        return client.hire_agent(capability, min_trust_score=min_trust_score)


def settle_contract(contract_id: str, output_data: Any, buyer_slug: str) -> Dict[str, Any]:
    """Convenience function: Settle a contract."""
    with A2AClient(buyer_slug=buyer_slug) as client:
        return client.settle_contract(contract_id, output_data)
