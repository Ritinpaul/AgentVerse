"""Request signing middleware — HMAC-SHA256 payload integrity verification.

Prevents:
  - Request tampering (payload modification in transit)
  - Replay attacks (timestamp window of ±300 seconds)

How it works:
  The caller constructs a signature string:
    METHOD\nPATH\nTIMESTAMP\nSHA256(body)

  Then signs it with their shared secret:
    X-Signature = HMAC-SHA256(secret, signature_string).hexdigest

Required headers:
  X-Timestamp  — Unix timestamp (integer seconds, UTC)
  X-Signature  — HMAC-SHA256 hex digest

Usage:
  # Apply to a single endpoint:
  @router.post("/high-value-action")
  async def action(
      _: None = Depends(verify_signature),
  ):
      ...

  # Disable for a specific request (testing):
  # Omit X-Signature header — will be rejected unless in development mode.

Client-side signing example (Python):
  import hashlib, hmac, time, json

  body = json.dumps({"action": "approve_payment", "amount": 50000})
  ts   = str(int(time.time))
  bh   = hashlib.sha256(body.encode).hexdigest
  msg  = f"POST\n/api/v1/sentinel/evaluate\n{ts}\n{bh}"
  sig  = hmac.new(SECRET.encode, msg.encode, hashlib.sha256).hexdigest

  headers = {
      "X-Timestamp": ts,
      "X-Signature": sig,
      "Content-Type": "application/json",
  }
"""

import hashlib
import hmac
import logging
import time
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

logger = logging.getLogger(__name__)

# Replay-attack window: reject requests older than this many seconds
_TIMESTAMP_TOLERANCE_S = 300


def _get_signing_secret() -> str:
    from config import get_settings
    return get_settings.request_signing_secret or get_settings.jwt_secret_key


def _compute_expected_signature(
    method: str,
    path: str,
    timestamp: str,
    body: bytes,
    secret: str,
) -> str:
    """Compute the expected HMAC-SHA256 signature for a request."""
    body_hash = hashlib.sha256(body).hexdigest
    message = f"{method.upper}\n{path}\n{timestamp}\n{body_hash}"
    return hmac.new(secret.encode, message.encode, hashlib.sha256).hexdigest


async def verify_signature(
    request: Request,
    x_timestamp: Annotated[str | None, Header(alias="X-Timestamp")] = None,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> None:
    """FastAPI dependency: verify HMAC-SHA256 request signature.

    Development bypass: when app_env == 'development' and no X-Signature
    header is present, the check is skipped with a debug warning.
    """
    from config import get_settings
    settings = get_settings()

    # ── Development bypass ──
    if settings.app_env == "development" and not x_signature:
        logger.debug("[SIGNING] Signature check skipped (dev mode, no header)")
        return

    # ── Require both headers ──
    if not x_timestamp or not x_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request signing required: X-Timestamp and X-Signature headers are missing.",
        )

    # ── Timestamp validation (replay attack prevention) ──
    try:
        ts = int(x_timestamp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Timestamp must be a Unix integer timestamp.",
        )

    now = int(time.time)
    age = abs(now - ts)
    if age > _TIMESTAMP_TOLERANCE_S:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Request timestamp is {age}s old (tolerance: {_TIMESTAMP_TOLERANCE_S}s). "
                "Possible replay attack."
            ),
        )

    # ── Read body ──
    body = await request.body

    # ── Compute and compare signatures (constant-time comparison) ──
    secret = _get_signing_secret
    expected = _compute_expected_signature(
        method=request.method,
        path=request.url.path,
        timestamp=x_timestamp,
        body=body,
        secret=secret,
    )

    if not hmac.compare_digest(expected, x_signature.lower):
        logger.warning(
            f"[SIGNING] Signature mismatch for {request.method} {request.url.path} "
            f"(ts={x_timestamp}, age={age}s)"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request signature is invalid. Verify your signing secret and message format.",
        )

    logger.debug(
        f"[SIGNING] Signature verified: {request.method} {request.url.path} (age={age}s)"
    )


def sign_request(
    method: str,
    path: str,
    body: str | bytes,
    secret: str,
) -> dict[str, str]:
    """Utility: generate X-Timestamp and X-Signature headers for a request.

    Use this in test clients and SDK connectors.

    Returns:
        {"X-Timestamp": "...", "X-Signature": "..."}
    """
    if isinstance(body, str):
        body = body.encode
    ts = str(int(time.time))
    sig = _compute_expected_signature(method, path, ts, body, secret)
    return {"X-Timestamp": ts, "X-Signature": sig}
