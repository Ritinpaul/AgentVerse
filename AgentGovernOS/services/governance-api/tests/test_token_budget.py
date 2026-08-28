"""Tests for TokenBudgetService."""
from __future__ import annotations

import fakeredis.aioredis as fakeredis
import pytest

from services.token_budget import DAILY_LIMIT, TokenBudgetService


@pytest.fixture
async def redis():
    r = fakeredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest.fixture
def budget(redis):
    return TokenBudgetService(redis)


@pytest.mark.asyncio
async def test_initial_status_is_zero(budget):
    status = await budget.get_status("user-123")
    assert status.used == 0
    assert status.remaining == DAILY_LIMIT
    assert not status.exceeded


@pytest.mark.asyncio
async def test_commit_increments(budget):
    await budget.commit("user-123", 1000)
    status = await budget.get_status("user-123")
    assert status.used == 1000
    assert status.remaining == DAILY_LIMIT - 1000


@pytest.mark.asyncio
async def test_check_does_not_increment(budget):
    status = await budget.check("user-123", estimated_tokens=500)
    # Check should not write to redis
    after = await budget.get_status("user-123")
    assert after.used == 0


@pytest.mark.asyncio
async def test_check_detects_limit_exceeded(budget):
    await budget.commit("user-123", DAILY_LIMIT - 100)
    status = await budget.check("user-123", estimated_tokens=200)
    assert status.exceeded is True


@pytest.mark.asyncio
async def test_exactly_at_limit_not_exceeded_on_check(budget):
    await budget.commit("user-123", DAILY_LIMIT)
    status = await budget.check("user-123", estimated_tokens=0)
    assert status.exceeded is False  # at limit but 0 extra


@pytest.mark.asyncio
async def test_one_token_over_limit_is_exceeded(budget):
    await budget.commit("user-123", DAILY_LIMIT)
    status = await budget.check("user-123", estimated_tokens=1)
    assert status.exceeded is True


@pytest.mark.asyncio
async def test_commit_over_limit_marks_exceeded(budget):
    await budget.commit("user-123", DAILY_LIMIT + 500)
    status = await budget.get_status("user-123")
    assert status.exceeded is True
    assert status.remaining == 0


@pytest.mark.asyncio
async def test_reset_clears_budget(budget):
    await budget.commit("user-123", 10_000)
    await budget.reset("user-123")
    status = await budget.get_status("user-123")
    assert status.used == 0


@pytest.mark.asyncio
async def test_different_users_are_isolated(budget):
    await budget.commit("user-A", 5_000)
    await budget.commit("user-B", 20_000)

    a = await budget.get_status("user-A")
    b = await budget.get_status("user-B")

    assert a.used == 5_000
    assert b.used == 20_000
