"""
Policy Distribution Service — versioned policy bundles with hash verification.

The control plane maintains a central policy store. The distribution service:
  1. Packages rules into versioned, hash-signed bundles
  2. Pushes bundles to all registered edge gateways
  3. Tracks which gateway has which version
  4. Supports rollback to any previous version
  5. Detects conflicts when edge overrides cloud policies

Bundle structure:
  {
    "version": "v2024.01.15-001",
    "rules": [...],
    "hash": "sha256:...",        ← integrity check
    "parent_hash": "sha256:...", ← chain to previous version
    "valid_from": ISO timestamp,
    "valid_until": ISO timestamp or null,
    "metadata": { author, description, change_type }
  }

Edge gateways verify the bundle hash before loading.
If hash mismatch → reject + alert (potential tampering).
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class PolicyRule:
    """A single policy rule definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4))
    name: str = ""
    type: str = ""                  # amount_limit, trust_minimum, tier_required, etc.
    parameters: dict = field(default_factory=dict)
    on_fail: str = "deny"           # deny | escalate
    environment_scope: list = field(default_factory=lambda: ["cloud", "edge", "client"])
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            **self.parameters,
            "on_fail": self.on_fail,
            "environment_scope": self.environment_scope,
            "active": self.active,
        }


@dataclass
class PolicyBundle:
    """A versioned, hash-verified collection of policy rules."""
    version: str
    rules: list[PolicyRule]
    hash: str = ""
    parent_hash: str = ""
    valid_from: datetime = field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime | None = None
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4))

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash

    def _compute_hash(self) -> str:
        payload = {
            "version": self.version,
            "rules": [r.to_dict for r in self.rules],
            "parent_hash": self.parent_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode).hexdigest

    def verify_integrity(self) -> bool:
        """Verify bundle has not been tampered with."""
        return self.hash == self._compute_hash

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "rules": [r.to_dict for r in self.rules],
            "hash": self.hash,
            "parent_hash": self.parent_hash,
            "valid_from": self.valid_from.isoformat,
            "valid_until": self.valid_until.isoformat if self.valid_until else None,
            "metadata": self.metadata,
            "rule_count": len(self.rules),
        }

    def to_edge_format(self) -> dict:
        """
        Lightweight format for edge gateway consumption.
        Only includes active rules scoped to the target environment.
        """
        return {
            "version": self.version,
            "hash": self.hash,
            "rules": [r.to_dict for r in self.rules if r.active],
        }


class PolicyDistributionService:
    """
    Central policy distribution — manages bundles and pushes to edge gateways.
    """

    def __init__(self):
        self._bundles: list[PolicyBundle] = []
        self._current: PolicyBundle | None = None
        self._gateway_versions: dict[str, str] = {}  # gateway_id → bundle version
        self._rollback_stack: list[str] = []          # version history for rollback

    # ──────────────────────────────────────────────
    # Bundle management
    # ──────────────────────────────────────────────

    def create_bundle(
        self,
        rules: list[PolicyRule],
        version: str = "",
        metadata: dict = None,
    ) -> PolicyBundle:
        """
        Create a new versioned policy bundle.
        Automatically hashes the rules and chains to the previous bundle.
        """
        if not version:
            version = f"v{datetime.now(UTC).strftime('%Y.%m.%d')}-{len(self._bundles) + 1:03d}"

        parent_hash = self._current.hash if self._current else ""

        bundle = PolicyBundle(
            version=version,
            rules=rules,
            parent_hash=parent_hash,
            metadata=metadata or {},
        )

        self._bundles.append(bundle)
        if self._current:
            self._rollback_stack.append(self._current.version)
        self._current = bundle

        logger.info(
            f"[POLICY-DIST] Bundle created: v={version} "
            f"rules={len(rules)} hash={bundle.hash[:12]}"
        )
        return bundle

    def get_current_bundle(self) -> PolicyBundle | None:
        return self._current

    def get_bundle_by_version(self, version: str) -> PolicyBundle | None:
        for b in self._bundles:
            if b.version == version:
                return b
        return None

    def rollback(self, target_version: str = "") -> PolicyBundle | None:
        """
        Roll back to a previous policy version.
        If target_version is empty, rolls back one step.
        """
        if target_version:
            target = self.get_bundle_by_version(target_version)
            if target:
                self._current = target
                logger.warning(f"[POLICY-DIST] Rolled back to {target_version}")
                return target
            return None

        if self._rollback_stack:
            prev_version = self._rollback_stack.pop
            return self.rollback(prev_version)

        return None

    def diff_bundles(self, v1: str, v2: str) -> dict:
        """
        Compare two bundles and return the diff.
        Returns added, removed, and modified rules.
        """
        b1 = self.get_bundle_by_version(v1)
        b2 = self.get_bundle_by_version(v2)
        if not b1 or not b2:
            return {"error": "Bundle not found"}

        r1_by_name = {r.name: r for r in b1.rules}
        r2_by_name = {r.name: r for r in b2.rules}

        added = [r.to_dict for name, r in r2_by_name.items if name not in r1_by_name]
        removed = [r.to_dict for name, r in r1_by_name.items if name not in r2_by_name]
        modified = []
        for name in set(r1_by_name.keys) & set(r2_by_name.keys):
            if r1_by_name[name].to_dict != r2_by_name[name].to_dict:
                modified.append({
                    "name": name,
                    "before": r1_by_name[name].to_dict,
                    "after": r2_by_name[name].to_dict,
                })

        return {
            "from_version": v1,
            "to_version": v2,
            "added": added,
            "removed": removed,
            "modified": modified,
            "total_changes": len(added) + len(removed) + len(modified),
        }

    # ──────────────────────────────────────────────
    # Gateway sync tracking
    # ──────────────────────────────────────────────

    def register_gateway_sync(self, gateway_id: str, version: str) -> None:
        """Record that a gateway has received a specific bundle version."""
        self._gateway_versions[gateway_id] = version

    def get_stale_gateways(self) -> list[str]:
        """Return gateways NOT running the current bundle version."""
        if not self._current:
            return []
        return [
            gid for gid, ver in self._gateway_versions.items
            if ver != self._current.version
        ]

    def get_gateway_status(self) -> dict:
        """Full sync status: which gateways have which version."""
        current_v = self._current.version if self._current else "none"
        return {
            "current_version": current_v,
            "gateways": {
                gid: {
                    "version": ver,
                    "up_to_date": ver == current_v,
                }
                for gid, ver in self._gateway_versions.items
            },
            "stale_count": len(self.get_stale_gateways),
        }

    # ──────────────────────────────────────────────
    # Scoped bundles for specific environments
    # ──────────────────────────────────────────────

    def get_bundle_for_environment(self, environment: str) -> dict | None:
        """
        Return a bundle with only rules that apply to a specific environment.
        E.g., edge gateways only get edge-scoped rules — not cloud-only rules.
        """
        if not self._current:
            return None

        scoped_rules = [
            r for r in self._current.rules
            if r.active and environment in r.environment_scope
        ]

        return {
            "version": self._current.version,
            "hash": self._current.hash,
            "rules": [r.to_dict for r in scoped_rules],
            "environment": environment,
            "total_rules": len(scoped_rules),
        }

    @property
    def version_count(self) -> int:
        return len(self._bundles)

    @property
    def version_history(self) -> list[str]:
        return [b.version for b in self._bundles]
