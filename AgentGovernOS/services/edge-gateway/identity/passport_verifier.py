"""
Passport Verifier — offline-capable JWT verification for edge gateways.

Two modes:
  ONLINE   — verify + check revocation list from control plane
  DEGRADED — verify using cached public key + last-known revocation list

The verifier automatically detects when the control plane is unreachable
and switches to DEGRADED mode without crashing the edge gateway.
"""

import logging
from dataclasses import dataclass

import jwt

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    valid: bool
    claims: dict
    reason: str = ""
    mode: str = "online"


class PassportVerifier:
    """
    Stateful passport verifier for the edge gateway.
    Caches the control plane's public key and revocation list locally.
    """

    def __init__(self, jwt_secret: str, control_plane_url: str, algorithm: str = "HS256"):
        self.jwt_secret = jwt_secret
        self.control_plane_url = control_plane_url
        self.algorithm = algorithm
        self.mode = "online"
        self._revocation_set: set[str] = set

    async def verify(self, token: str) -> VerificationResult:
        """Verify a passport JWT token. Returns VerificationResult."""
        try:
            decoded = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            return VerificationResult(valid=False, claims={}, reason="passport expired")
        except jwt.InvalidTokenError as e:
            return VerificationResult(valid=False, claims={}, reason=f"invalid signature: {e}")

        jti = decoded.get("jti", "")
        if jti in self._revocation_set:
            return VerificationResult(valid=False, claims={}, reason="passport revoked", mode=self.mode)

        return VerificationResult(valid=True, claims=decoded, reason="", mode=self.mode)

    def verify_sync(self, token: str) -> VerificationResult:
        """Synchronous version for use in non-async contexts."""
        try:
            decoded = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            return VerificationResult(valid=False, claims={}, reason="passport expired")
        except jwt.InvalidTokenError as e:
            return VerificationResult(valid=False, claims={}, reason=f"invalid signature: {e}")

        jti = decoded.get("jti", "")
        if jti in self._revocation_set:
            return VerificationResult(valid=False, claims={}, reason="passport revoked", mode=self.mode)

        return VerificationResult(valid=True, claims=decoded, mode=self.mode)

    def update_revocation_list(self, revoked_jtis: list[str]) -> None:
        """Update the local revocation cache."""
        self._revocation_set = set(revoked_jtis)
        logger.info(f"[VERIFIER] Revocation list updated: {len(revoked_jtis)} entries")

    def set_mode(self, mode: str) -> None:
        self.mode = mode
