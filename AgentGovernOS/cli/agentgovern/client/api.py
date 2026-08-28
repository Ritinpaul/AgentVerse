"""
Governance API Client — talks to the AgentGovern OS server.

Used to sync ABOM results, register agents, fetch audit logs, and more.
All operations gracefully degrade when the server is unavailable.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class GovernanceAPIClient:
    """HTTP client for the AgentGovern Governance API."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = os.getenv("AGENTGOVERN_API_KEY", "")

    @property
    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def health(self) -> bool:
        """Return True if the server is reachable."""
        try:
            r = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return r.status_code == 200
        except httpx.RequestError:
            return False

    def list_agents(self) -> list[dict[str, Any]]:
        """Fetch all registered agents from the server."""
        try:
            r = httpx.get(
                f"{self.base_url}/api/v1/agents",
                headers=self._headers,
                timeout=self.timeout,
            )
            r.raise_for_status
            return r.json.get("agents", [])
        except httpx.RequestError as e:
            raise ConnectionError(f"Cannot connect to server at {self.base_url}: {e}") from e

    def register_agent(self, agent_data: dict[str, Any]) -> dict[str, Any]:
        """Register a new agent on the server. Returns response dict."""
        try:
            r = httpx.post(
                f"{self.base_url}/api/v1/agents",
                json=agent_data,
                headers=self._headers,
                timeout=self.timeout,
            )
            if r.status_code == 409:
                # Already exists — update it
                code = agent_data.get("code", agent_data.get("agent_code", ""))
                r = httpx.put(
                    f"{self.base_url}/api/v1/agents/{code}",
                    json=agent_data,
                    headers=self._headers,
                    timeout=self.timeout,
                )
            r.raise_for_status
            return r.json
        except httpx.RequestError as e:
            raise ConnectionError(f"Cannot connect to server at {self.base_url}: {e}") from e

    def get_agent(self, agent_code: str) -> dict[str, Any]:
        """Fetch a single agent by code."""
        try:
            r = httpx.get(
                f"{self.base_url}/api/v1/agents/{agent_code}",
                headers=self._headers,
                timeout=self.timeout,
            )
            r.raise_for_status
            return r.json
        except httpx.RequestError as e:
            raise ConnectionError(f"Cannot connect to server at {self.base_url}: {e}") from e

    def upload_abom(self, abom: dict[str, Any]) -> dict[str, Any]:
        """Upload a complete ABOM scan result to the server for ingestion."""
        try:
            r = httpx.post(
                f"{self.base_url}/api/v1/abom",
                json=abom,
                headers=self._headers,
                timeout=self.timeout * 3,  # Larger payload
            )
            r.raise_for_status
            return r.json
        except httpx.RequestError as e:
            raise ConnectionError(f"Cannot connect to server at {self.base_url}: {e}") from e

    def fetch_audit_logs(
        self,
        limit: int = 50,
        since: str | None = None,
        agent_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent audit log entries from the server."""
        params: dict[str, Any] = {"limit": limit}
        if since:
            params["since"] = since
        if agent_code:
            params["agent_code"] = agent_code
        try:
            r = httpx.get(
                f"{self.base_url}/api/v1/audit-logs",
                params=params,
                headers=self._headers,
                timeout=self.timeout,
            )
            r.raise_for_status
            data = r.json
            return data if isinstance(data, list) else data.get("logs", [])
        except httpx.RequestError as e:
            raise ConnectionError(f"Cannot connect to server at {self.base_url}: {e}") from e
