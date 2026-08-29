"""
x402 Micropayment Protocol Guard — Agent-to-Agent Payment Header Verification
Enforces HTTP 402 Payment Required status and header standards when monetized APIs are invoked.
"""
from fastapi import Header, HTTPException, status
from typing import Optional

def require_x402_payment(price_usd: float = 0.001):
    """
    FastAPI dependency factory enforcing x402 payment header verification.
    If X-402-Payment-Token or Authorization header is missing or invalid,
    raises HTTP 402 Payment Required with WWW-Authenticate header.
    """
    async def _x402_guard(
        x_402_payment_token: Optional[str] = Header(default=None, alias="X-402-Payment-Token"),
        authorization: Optional[str] = Header(default=None),
    ):
        token = x_402_payment_token
        if not token and authorization and authorization.lower().startswith("x402 "):
            token = authorization.split(" ", 1)[1]

        if not token or len(token.strip()) < 8:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Payment Required. Required price: ${price_usd:.4f} USD.",
                headers={
                    "WWW-Authenticate": f'x402 realm="AgentStore Micro-transactions", price_usd="{price_usd}"',
                    "X-402-Price-USD": str(price_usd),
                },
            )
        return {"payment_token": token, "price_usd": price_usd}

    return _x402_guard
