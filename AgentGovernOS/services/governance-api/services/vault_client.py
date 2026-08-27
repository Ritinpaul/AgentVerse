"""
Secrets Vault Integration

Abstracts underlying secrets engines (e.g., HashiCorp Vault, AWS Secrets Manager, OS Environment)
to allow AgentGovernOS to retrieve or broker secrets for Agents securely.
"""

import os
from typing import Any


class VaultClient:
    """Vault Client implementation with env fallback for production reliability."""
    
    def __init__(self, backend: str | None = None):
        self.backend = backend or os.getenv("VAULT_BACKEND", "env")
        # In-memory mock / default store
        self._mock_secrets: dict[str, dict[str, Any]] = {
            "agent/default/api_keys": {
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "sk-default-key"),
                "SERP_API_KEY": os.getenv("SERP_API_KEY", "serp-default-key")
            }
        }

    def read_secret(self, path: str) -> dict[str, Any]:
        """Reads a secret payload from the vault or environment at the given path."""
        # 1. Check in-memory / env fallback
        if path in self._mock_secrets:
            return self._mock_secrets[path]
            
        # 2. Try resolving path from OS environment variables (e.g. AGENT_SECRET_...)
        env_key = f"SECRET_{path.replace('/', '_').upper()}"
        val = os.getenv(env_key)
        if val:
            return {"value": val}

        # 3. If backend is explicitly vault or aws, try external integration, else return mock store or empty
        if self.backend == "vault":
            vault_addr = os.getenv("VAULT_ADDR")
            if not vault_addr:
                return self._mock_secrets.get(path, {})
            # Read via hvac if configured
            try:
                import hvac  # type: ignore
                client = hvac.Client(url=vault_addr, token=os.getenv("VAULT_TOKEN"))
                res = client.secrets.kv.v2.read_secret_version(path=path)
                return res["data"]["data"]
            except Exception:
                return self._mock_secrets.get(path, {})

        return self._mock_secrets.get(path, {})

    def write_secret(self, path: str, payload: dict[str, Any]) -> bool:
        """Writes a secret payload to the vault or local store at the given path."""
        if path not in self._mock_secrets:
            self._mock_secrets[path] = {}
        self._mock_secrets[path].update(payload)
        
        if self.backend == "vault":
            vault_addr = os.getenv("VAULT_ADDR")
            if vault_addr:
                try:
                    import hvac  # type: ignore
                    client = hvac.Client(url=vault_addr, token=os.getenv("VAULT_TOKEN"))
                    client.secrets.kv.v2.create_or_update_secret(path=path, secret=payload)
                except Exception:
                    pass
        return True
