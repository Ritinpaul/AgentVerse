"""
Control Plane Sync Client — syncs policy bundles, revocation lists, and local ledger.
"""

import logging

import httpx

logger = logging.getLogger(__name__)


class ControlPlaneSyncClient:
    """
    Responsible for bidirectional sync between the Edge Gateway and Control Plane.
    Run as a background asyncio task every SYNC_INTERVAL_SECONDS.
    """

    def __init__(self, control_plane_url: str, gateway_id: str, timeout: float = 5.0):
        self.control_plane_url = control_plane_url.rstrip("/")
        self.gateway_id = gateway_id
        self.timeout = timeout

    async def sync_policies(self, enforcer) -> dict:
        """Download latest policy bundle from control plane and load into enforcer."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(f"{self.control_plane_url}/sentinel/policies/bundle")
                if r.status_code == 200:
                    data = r.json
                    rules = data.get("rules", [])
                    version = data.get("version", "unknown")
                    enforcer.load_policy_bundle(rules, version)
                    logger.info(f"[SYNC] Policies updated: {len(rules)} rules v{version}")
                    return {"status": "synced", "rules": len(rules), "version": version}
        except Exception as e:
            logger.warning(f"[SYNC] Policy sync failed (degraded mode): {e}")
        return {"status": "failed"}

    async def sync_revocation_list(self, verifier) -> dict:
        """Download latest passport revocation list from control plane."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(f"{self.control_plane_url}/identity/revocation-list")
                if r.status_code == 200:
                    data = r.json
                    jtis = data.get("revoked_jtis", [])
                    verifier.update_revocation_list(jtis)
                    logger.info(f"[SYNC] Revocation list updated: {len(jtis)} entries")
                    return {"status": "synced", "revoked_count": len(jtis)}
        except Exception as e:
            logger.warning(f"[SYNC] Revocation sync failed: {e}")
        return {"status": "failed"}

    async def flush_ledger(self, ledger) -> dict:
        """Push unsynced local ledger entries to the control plane."""
        unsynced = ledger.get_unsynced
        if not unsynced:
            return {"status": "nothing_to_flush"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{self.control_plane_url}/ancestor/bulk-record",
                    json={
                        "gateway_id": self.gateway_id,
                        "decisions": [e.to_dict for e in unsynced],
                    },
                )
                if r.status_code == 200:
                    ids = [e.id for e in unsynced]
                    synced = ledger.mark_synced(ids)
                    logger.info(f"[SYNC] Flushed {synced} ledger entries to control plane")
                    return {"status": "flushed", "count": synced}
        except Exception as e:
            logger.warning(f"[SYNC] Ledger flush failed: {e}")
        return {"status": "failed", "buffered": len(unsynced)}
