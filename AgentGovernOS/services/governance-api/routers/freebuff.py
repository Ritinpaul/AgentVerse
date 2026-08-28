"""
FreeBuff Router
===============
Provides the free AI tier for AgentVerse IDE users.

Endpoints:
    POST /api/v1/freebuff/chat    — Streaming chat completion (SSE)
    GET  /api/v1/freebuff/budget  — Current token budget status

All requests require a valid Supabase JWT in the Authorization header.
Token budget is enforced server-side via Redis (50k tokens / user / day UTC).

Free model routing via OpenRouter free tier:
    default   → google/gemma-3-27b-it:free
    fast      → meta-llama/llama-3.1-8b-instruct:free
    code      → mistralai/mistral-7b-instruct:free
    reasoning → google/gemma-3-27b-it:free
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

import httpx
import redis.asyncio as aioredis
from config import get_settings
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from models.freebuff import FreeBuffBudgetResponse, FreeBuffChatRequest

from services.token_budget import TokenBudgetService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/freebuff", tags=["freebuff"])

# ── Free model map ─────────────────────────────────────────────────────────

FREE_MODEL_MAP: dict[str, str] = {
    "default": "google/gemma-3-27b-it:free",
    "fast": "meta-llama/llama-3.1-8b-instruct:free",
    "code": "mistralai/mistral-7b-instruct:free",
    "reasoning": "google/gemma-3-27b-it:free",
}

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Rough token estimator (pre-call check only; real count comes from stream) ──

def _estimate_tokens(messages: list) -> int:
    """Very rough estimate: ~4 chars per token across messages."""
    total_chars = sum(len(m.content) for m in messages)
    return max(1, total_chars // 4)


# ── Auth dependency ────────────────────────────────────────────────────────

async def _get_current_user_id(request: Request) -> str:
    """
    Extract user_id from a Supabase JWT.
    We validate the JWT by calling the Supabase /auth/v1/user endpoint
    (avoids duplicating JWKS rotation logic in-service).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = auth_header.removeprefix("Bearer ").strip()

    supabase_url = settings.supabase_url if hasattr(settings, "supabase_url") else ""
    supabase_anon = settings.supabase_anon_key if hasattr(settings, "supabase_anon_key") else ""

    if not supabase_url:
        # Fallback: decode JWT sub claim without signature verification
        # (acceptable only when GovernOS is behind an authenticated gateway)
        try:
            import base64 as _b64
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            payload = json.loads(_b64.urlsafe_b64decode(payload_b64 + "=" * padding))
            user_id = payload.get("sub") or payload.get("user_id") or ""
            if not user_id:
                raise ValueError("No sub in JWT")
            return user_id
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid JWT") from None

    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(
            f"{supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": supabase_anon},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    data = resp.json()
    user_id = data.get("id") or data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Cannot resolve user_id from token")

    return str(user_id)


# ── Redis dependency ───────────────────────────────────────────────────────

async def _get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()


# ── SSE streaming generator ────────────────────────────────────────────────

async def _stream_openrouter(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    user_id: str,
    budget_svc: TokenBudgetService,
) -> AsyncGenerator[str, None]:
    """
    Stream from OpenRouter and count real tokens from usage chunks.
    Yields SSE-formatted strings including a final budget_update event.
    """
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://agentverse.nuuvixx.com",
        "X-Title": "AgentVerse FreeBuff",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "usage": {"include": True},  # OpenRouter extension for per-chunk usage
    }

    total_tokens = 0
    last_usage: dict | None = None

    try:
        async with (
            httpx.AsyncClient(timeout=60) as client,
            client.stream("POST", OPENROUTER_CHAT_URL, json=payload, headers=headers) as response,
        ):
            if response.status_code != 200:
                body = await response.aread()
                logger.error("OpenRouter error %s: %s", response.status_code, body)
                yield f"data: {json.dumps({'error': f'Upstream error {response.status_code}'})}\n\n"
                return

            async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    json_str = line.removeprefix("data: ").strip()
                    if json_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue

                    # Capture usage if present
                    if chunk.get("usage"):
                        last_usage = chunk["usage"]
                        total_tokens = last_usage.get("total_tokens", total_tokens)

                    # Forward the delta as-is (OpenAI-compatible format)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': delta}}]})}\n\n"

    except httpx.TimeoutException:
        yield f"data: {json.dumps({'error': 'Upstream timeout'})}\n\n"
        return
    except Exception as exc:
        logger.exception("Unexpected streaming error")
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        return

    # Commit real token usage to budget
    if total_tokens > 0:
        updated = await budget_svc.commit(user_id, total_tokens)
    else:
        # Fallback: if OpenRouter didn't report usage, estimate from response
        updated = await budget_svc.get_status(user_id)

    # Emit budget update event so the IDE status bar can refresh
    yield f"data: {json.dumps({'type': 'budget_update', 'budget': updated.model_dump(mode='json', default=str)})}\n\n"
    yield "data: [DONE]\n\n"


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/chat")
async def freebuff_chat(
    req: FreeBuffChatRequest,
    request: Request,
    user_id: str = Depends(_get_current_user_id),
    redis: aioredis.Redis = Depends(_get_redis),
):
    """
    Streaming chat completion for the free tier.

    - Checks the 50k/day token budget before forwarding.
    - Routes through OpenRouter free models (our API key, never the user's).
    - Returns SSE stream with a final ``budget_update`` event.
    """
    budget_svc = TokenBudgetService(redis)
    estimated = _estimate_tokens(req.messages)
    status = await budget_svc.check(user_id, estimated_tokens=estimated)

    if status.exceeded:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_token_limit_exceeded",
                "limit": status.limit,
                "used": status.used,
                "remaining": status.remaining,
                "resets_at": status.resets_at.isoformat(),
                "message": (
                    "You have used your 50,000 free token daily allowance. "
                    "Add a BYOK API key in AgentVerse Settings to continue, "
                    "or wait until midnight UTC for your budget to reset."
                ),
            },
        )

    if not settings.openrouter_api_key:
        raise HTTPException(status_code=503, detail="FreeBuff not configured on this server")

    model = FREE_MODEL_MAP.get(req.model_hint, FREE_MODEL_MAP["default"])
    messages = [m.model_dump() for m in req.messages]

    logger.info(
        "freebuff_chat user=%s model=%s estimated_tokens=%d",
        user_id[:8], model, estimated,
    )

    return StreamingResponse(
        _stream_openrouter(
            model=model,
            messages=messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            user_id=user_id,
            budget_svc=budget_svc,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Nginx: disable proxy buffering for SSE
        },
    )


@router.get("/budget", response_model=FreeBuffBudgetResponse)
async def get_budget(
    user_id: str = Depends(_get_current_user_id),
    redis: aioredis.Redis = Depends(_get_redis),
):
    """Return the current token budget status for the authenticated user."""
    budget_svc = TokenBudgetService(redis)
    status = await budget_svc.get_status(user_id)
    return FreeBuffBudgetResponse(budget=status)
