"""
Environment Registry — tracks where agents are running.

Each agent sends a heartbeat every 30 seconds from wherever it's executing.
The registry determines:
  - Is the agent alive? (last_heartbeat < 90s ago)
  - Where is it running? (cloud / edge / client)
  - What's its current execution context?
  - Are there unauthorized environment crossings? (triggers alert)

This is the foundation for the Fleet Command Center dashboard —
a real-time map of agents across your distributed infrastructure.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

ENVIRONMENT_TYPES = {"cloud", "edge", "client", "on-premise"}
HEARTBEAT_TTL_SECONDS = 90   # Agent considered dead after 90s
STALE_AFTER_SECONDS = 300    # Show as "stale" in fleet dashboard after 300s


@dataclass
class AgentLocation:
    """A single heartbeat record from an agent."""
    agent_id: str
    environment: str                 # cloud | edge | client | on-premise
    host_id: str                     # VM ID, edge device ID, or client machine ID
    region: str = ""                 # GCP us-central1, AWS ap-south-1, etc.
    ip_address: str = ""
    agent_version: str = ""
    passport_jti: str = ""
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        age = (datetime.now(UTC) - self.last_seen).total_seconds
        return age < HEARTBEAT_TTL_SECONDS

    @property
    def status(self) -> str:
        age = (datetime.now(UTC) - self.last_seen).total_seconds
        if age < HEARTBEAT_TTL_SECONDS:
            return "alive"
        elif age < STALE_AFTER_SECONDS:
            return "stale"
        return "dead"

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "environment": self.environment,
            "host_id": self.host_id,
            "region": self.region,
            "ip_address": self.ip_address,
            "agent_version": self.agent_version,
            "passport_jti": self.passport_jti,
            "last_seen": self.last_seen.isoformat,
            "status": self.status,
            "is_alive": self.is_alive,
            "metadata": self.metadata,
        }


class EnvironmentRegistry:
    """
    In-memory environment registry (backed by Redis in production).

    Exposes:
      heartbeat      — agent phones home
      get_location   — where is this agent now?
      fleet_status   — full view: all agents + their locations + health
      detect_crossing— alert when agent moves to unauthorized environment
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._locations: dict[str, AgentLocation] = {}   # agent_id → location
        self._history: dict[str, list[str]] = {}          # agent_id → [env, env, ...]
        self._alerts: list[dict] = []

    def heartbeat(
        self,
        agent_id: str,
        environment: str,
        host_id: str,
        passport_jti: str = "",
        region: str = "",
        ip_address: str = "",
        agent_version: str = "",
        metadata: dict = None,
    ) -> dict:
        """
        Process an agent heartbeat.

        Returns:
            {"status": "ok" | "alert", "message": str}
        """
        if environment not in ENVIRONMENT_TYPES:
            return {"status": "error", "message": f"Unknown environment: {environment}"}

        previous = self._locations.get(agent_id)
        prev_env = previous.environment if previous else None

        location = AgentLocation(
            agent_id=agent_id,
            environment=environment,
            host_id=host_id,
            region=region,
            ip_address=ip_address,
            agent_version=agent_version,
            passport_jti=passport_jti,
            last_seen=datetime.now(UTC),
            metadata=metadata or {},
        )
        self._locations[agent_id] = location

        # Track environment history
        if agent_id not in self._history:
            self._history[agent_id] = []
        self._history[agent_id].append(environment)

        # Detect unauthorized environment crossing
        if prev_env and prev_env != environment:
            alert = self._check_crossing(agent_id, prev_env, environment, location)
            if alert:
                return {"status": "alert", "alert": alert}

        logger.debug(
            f"[REGISTRY] Heartbeat: agent={agent_id[:8]} env={environment} region={region}"
        )
        return {"status": "ok", "location": location.to_dict}

    def get_location(self, agent_id: str) -> AgentLocation | None:
        return self._locations.get(agent_id)

    def fleet_status(self) -> dict:
        """Full fleet view: agents grouped by environment and status."""
        by_env: dict[str, list] = {}
        status_counts = {"alive": 0, "stale": 0, "dead": 0}

        for loc in self._locations.values:
            env = loc.environment
            if env not in by_env:
                by_env[env] = []
            by_env[env].append(loc.to_dict)
            status_counts[loc.status] = status_counts.get(loc.status, 0) + 1

        return {
            "total_agents": len(self._locations),
            "by_environment": {k: len(v) for k, v in by_env.items},
            "status_counts": status_counts,
            "agents": {aid: loc.to_dict for aid, loc in self._locations.items},
            "recent_alerts": self._alerts[-10:],
            "snapshot_at": datetime.now(UTC).isoformat,
        }

    def get_environment_history(self, agent_id: str) -> list[str]:
        """Return the sequence of environments an agent has visited."""
        return self._history.get(agent_id, [])

    def get_agents_in_environment(self, environment: str, alive_only: bool = True) -> list[AgentLocation]:
        """Return all agent locations in a given environment."""
        return [
            loc for loc in self._locations.values
            if loc.environment == environment and (not alive_only or loc.is_alive)
        ]

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    def _check_crossing(self, agent_id: str, from_env: str, to_env: str, location: AgentLocation) -> dict | None:
        """
        Detect potentially suspicious environment crossings.
        Crossing client → cloud without going through edge is flagged.
        """
        suspicious_paths = {
            ("client", "cloud"),   # Skipped edge gateway — data exfiltration risk
        }

        if (from_env, to_env) in suspicious_paths:
            alert = {
                "type": "unauthorized_environment_crossing",
                "agent_id": agent_id,
                "from": from_env,
                "to": to_env,
                "host_id": location.host_id,
                "timestamp": datetime.now(UTC).isoformat,
                "severity": "high",
            }
            self._alerts.append(alert)
            logger.warning(
                f"[REGISTRY] ALERT: Agent {agent_id[:8]} crossed {from_env} → {to_env} directly"
            )
            return alert

        return None
