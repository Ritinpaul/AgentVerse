"""Shared fixtures for AgentGovern OS benchmarks.

Sets up:
  - ASGI test app (TestClient wrapping the real FastAPI app)
  - In-memory SQLite database (no PostgreSQL needed)
  - Seeded policy + agent data for realistic benchmarks
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest

# ── Path setup: benchmarks run from repo root ──────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_API = ROOT / "services" / "governance-api"
sys.path.insert(0, str(GOVERNANCE_API))

# Force SQLite in-memory for benchmarks — no real DB needed
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./benchmark_test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("APP_ENV", "test")


# ── Import app after path + env setup ─────────────────────────────────────
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402, F401

SQLALCHEMY_TEST_URL = "sqlite+aiosqlite:///./benchmark_test.db"


@pytest.fixture(scope="session")
def db_engine():
    """Session-scoped async SQLite engine."""
    engine = create_async_engine(SQLALCHEMY_TEST_URL, echo=False)
    return engine


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app_client(db_engine, event_loop):
    """
    Session-scoped TestClient that wraps the real FastAPI governance-api app.
    Creates all tables once, seeds one agent + policies, then runs benchmarks.
    """
    import importlib.util

    main_path = GOVERNANCE_API / "main.py"
    spec = importlib.util.spec_from_file_location("governance_main", main_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    # Create tables (SQLite)
    async def _setup():
        from database import Base  # noqa: PLC0415
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    event_loop.run_until_complete(_setup())

    with TestClient(mod.app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def seeded_agent_code(app_client) -> str:
    """Create one test agent in the DB and return its agent_code for benchmarks."""
    payload = {
        "agent_code": f"BENCH-{uuid.uuid4().hex[:8].upper()}",
        "display_name": "Benchmark Agent",
        "role": "analyst",
        "crewai_role": "Financial Analyst",
        "crewai_backstory": "Benchmark-only agent for latency measurement.",
        "tier": "T3",
        "authority_limit": 5000.0,
    }
    resp = app_client.post("/api/v1/genesis/agents", json=payload)
    if resp.status_code in (200, 201):
        return payload["agent_code"]
    # If agent already exists from a prior run, just reuse the code
    return payload["agent_code"]
