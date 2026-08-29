"""
Startup Guard — Refuse SQLite in production environments (GAP-NEW-03).
"""
from __future__ import annotations


def refuse_sqlite_in_production(database_url: str, app_env: str) -> None:
    """
    Ensure production profiles refuse to start if DATABASE_URL resolves to SQLite.
    Prevents silent fallback to ephemeral or unpersisted local SQLite databases.
    """
    if app_env.lower() == "production" and (
        database_url.startswith("sqlite") or "sqlite" in database_url.lower()
    ):
        raise RuntimeError(
            f"APP_ENV=production but DATABASE_URL points to SQLite ({database_url}). "
            "Refusing to start. Set DATABASE_URL to a PostgreSQL connection string."
        )
