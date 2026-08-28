"""FreeBuff Pydantic schemas — request / response models for the free AI tier."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class FreeBuffChatRequest(BaseModel):
    """Request body for the FreeBuff /chat endpoint."""

    messages: list[ChatMessageSchema] = Field(..., min_length=1)
    model_hint: Literal["default", "fast", "code", "reasoning"] = "default"
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class BudgetStatus(BaseModel):
    """Current token-budget state for a user."""

    used: int
    remaining: int
    limit: int
    resets_at: datetime
    exceeded: bool


class FreeBuffBudgetResponse(BaseModel):
    """Response for GET /api/v1/freebuff/budget."""

    budget: BudgetStatus
