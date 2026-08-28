"""
Agent Passport Service — Distributed Identity for AI Agents

An Agent Passport is a signed JWT token that:
  1. Proves agent identity (cryptographic signature)
  2. Carries embedded DNA fingerprint (capability hash)
  3. Declares trust tier and authority limits
  4. Specifies allowed environments (cloud / edge / client)
  5. Includes expiry + rotation policy

Passport lifecycle:
  ISSUED  → agent registered in GENESIS → passport minted
  ACTIVE  → agent executing → passport verified on every action
  ROTATED → trust tier changes → new passport issued, old revoked
  REVOKED → agent suspended → passport blacklisted, all actions blocked

Privacy guarantee:
  The DNA fingerprint in the passport is a SHA-256 hash of the agent's
  dominant genes — it proves capability without exposing raw gene data.

Cross-environment portability:
  The same passport JWT is verifiable at:
    - Control Plane  (online, using JWKS from Passport Service)
    - Edge Gateway   (offline, using cached public key + revocation list)
    - Client SDK     (online fallback, offline if edge not reachable)
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import jwt

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Passport data model
# ──────────────────────────────────────────────

VALID_ENVIRONMENTS = {"cloud", "edge", "client", "on-premise"}
TIER_AUTHORITY_LIMITS = {
    "T1": 100_000,
    "T2": 50_000,
    "T3": 10_000,
    "T4": 0,
}


@dataclass
class AgentPassport:
    """
    Issued to an agent upon registration or trust-tier change.
    Serializes into a signed JWT via PassportService.issue.
    """
    agent_id: str
    agent_name: str
    agent_role: str
    tier: str                          # T1, T2, T3, T4
    trust_score: float                 # 0.0 – 1.0
    allowed_environments: list[str]    # ["cloud", "edge", "client"]
    dna_fingerprint: str               # SHA-256 of dominant genes
    authority_limit: float = 0.0      # Derived from tier
    issuer: str = "agentgovern-control-plane"
    jti: str = field(default_factory=lambda: str(uuid.uuid4))
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    revoked: bool = False

    def __post_init__(self):
        if not self.expires_at:
            self.expires_at = self.issued_at + timedelta(hours=24)
        if not self.authority_limit:
            self.authority_limit = TIER_AUTHORITY_LIMITS.get(self.tier, 0)
        # Validate environments
        invalid = set(self.allowed_environments) - VALID_ENVIRONMENTS
        if invalid:
            raise ValueError(f"Invalid environments: {invalid}. Must be one of {VALID_ENVIRONMENTS}")

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired

    def allows_environment(self, env: str) -> bool:
        return env in self.allowed_environments


# ──────────────────────────────────────────────
# DNA Fingerprint helper
# ──────────────────────────────────────────────

def compute_dna_fingerprint(dominant_genes: list[dict]) -> str:
    """
    Compute a privacy-preserving fingerprint from dominant genes.

    The fingerprint is a SHA-256 hash of (gene_name, gene_type, strength)
    tuples sorted deterministically. It proves capability without
    exposing raw gene text (e.g. settlement strategies).
    """
    if not dominant_genes:
        return hashlib.sha256(b"no-genes").hexdigest

    gene_summary = sorted([
        f"{g.get('gene_name', '')}:{g.get('gene_type', '')}:{round(g.get('strength', 0), 2)}"
        for g in dominant_genes
    ])
    payload = json.dumps(gene_summary, sort_keys=True).encode
    return hashlib.sha256(payload).hexdigest


# ──────────────────────────────────────────────
# Passport Service
# ──────────────────────────────────────────────

class PassportService:
    """
    Issues, verifies, rotates, and revokes Agent Passports.

    Uses RS256 (asymmetric) in production — caller provides private/public keys.
    For dev/testing, falls back to HS256 with a shared secret.
    """

    ALG_PROD = "RS256"
    ALG_DEV = "HS256"

    def __init__(
        self,
        private_key: str,             # RSA private key PEM or HS256 secret
        public_key: str,              # RSA public key PEM or same HS256 secret
        algorithm: str = "HS256",     # HS256 for dev, RS256 for production
        token_ttl_hours: int = 24,
    ):
        self.private_key = private_key
        self.public_key = public_key
        self.algorithm = algorithm
        self.token_ttl = timedelta(hours=token_ttl_hours)
        self._revocation_set: set[str] = set  # in-memory; back to Redis in prod

    def issue(self, passport: AgentPassport) -> str:
        """
        Sign and issue a JWT passport token.

        JWT claims:
            sub   : agent_id
            jti   : unique token ID (for revocation)
            iss   : issuer (agentgovern-control-plane)
            iat   : issued at
            exp   : expires at
            ag    : agentgovern-specific claims (role, tier, dna, envs, limits)
        """
        now = datetime.now(UTC)
        payload = {
            "sub": passport.agent_id,
            "jti": passport.jti,
            "iss": passport.issuer,
            "iat": int(now.timestamp),
            "exp": int(passport.expires_at.timestamp),
            "ag": {
                "name": passport.agent_name,
                "role": passport.agent_role,
                "tier": passport.tier,
                "trust_score": round(passport.trust_score, 4),
                "authority_limit": passport.authority_limit,
                "allowed_environments": passport.allowed_environments,
                "dna_fingerprint": passport.dna_fingerprint,
            },
        }

        token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)
        logger.info(
            f"[PASSPORT] Issued: agent={passport.agent_id[:8]} "
            f"tier={passport.tier} envs={passport.allowed_environments} "
            f"jti={passport.jti[:8]}"
        )
        return token

    def verify(self, token: str) -> dict:
        """
        Verify and decode a passport JWT.

        Returns the decoded payload dict.
        Raises:
            jwt.ExpiredSignatureError   — token has expired
            jwt.InvalidTokenError       — signature invalid or malformed
            ValueError                  — token has been revoked
        """
        decoded = jwt.decode(
            token,
            self.public_key,
            algorithms=[self.algorithm],
            options={"verify_exp": True},
        )

        jti = decoded.get("jti", "")
        if jti in self._revocation_set:
            raise ValueError(f"Passport revoked: jti={jti[:8]}")

        return decoded

    def revoke(self, jti: str) -> None:
        """Revoke a passport by JTI. Syncs to Redis in production."""
        self._revocation_set.add(jti)
        logger.warning(f"[PASSPORT] Revoked: jti={jti[:8]}")

    def rotate(self, old_token: str, new_passport: AgentPassport) -> str:
        """
        Revoke the old passport and issue a new one.
        Called on trust-tier change (promotion/demotion).
        """
        try:
            old_decoded = self.verify(old_token)
            self.revoke(old_decoded.get("jti", ""))
        except Exception:
            pass  # Already invalid — still issue new one
        return self.issue(new_passport)

    def extract_claims(self, token: str) -> dict:
        """
        Decode without verification — only for internal use where
        signature has already been verified at the edge.
        """
        return jwt.decode(token, options={"verify_signature": False})

    def is_revoked(self, jti: str) -> bool:
        return jti in self._revocation_set

    def get_revocation_list(self) -> list[str]:
        """Export revoked JTIs — pushed to edge gateways for offline enforcement."""
        return list(self._revocation_set)
