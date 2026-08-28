"""
Tests: database.py — engine, session, Base, get_db, init_db

Covers the AsyncEngine setup, session dependency, and init_db table creation
using mocks so no real database connection is needed.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "governance-api"))


class TestDatabaseModule:
    """Test engine and session factory creation."""

    def test_base_is_declarative(self):
        """Base should be a SQLAlchemy DeclarativeBase."""
        from database import Base
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)

    def test_async_session_factory_exists(self):
        """async_session should be an async_sessionmaker."""
        from database import async_session
        from sqlalchemy.ext.asyncio import async_sessionmaker
        assert isinstance(async_session, async_sessionmaker)

    def test_engine_exists(self):
        """engine should be an AsyncEngine."""
        from database import engine
        from sqlalchemy.ext.asyncio import AsyncEngine
        assert isinstance(engine, AsyncEngine)


class TestGetDb:
    """Test the get_db dependency generator."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session_and_commits(self):
        """get_db should yield a session, commit, and close it."""
        from database import get_db

        mock_session = AsyncMock
        mock_session.commit = AsyncMock
        mock_session.rollback = AsyncMock
        mock_session.close = AsyncMock

        mock_ctx = MagicMock
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("database.async_session", return_value=mock_ctx):
            gen = get_db
            session = await gen.__anext__
            assert session is mock_session
            try:
                await gen.athrow(StopAsyncIteration)
            except StopAsyncIteration:
                pass

    @pytest.mark.asyncio
    async def test_get_db_rolls_back_on_exception(self):
        """get_db should rollback when an exception occurs inside the block."""
        from database import get_db

        mock_session = AsyncMock
        mock_session.commit = AsyncMock
        mock_session.rollback = AsyncMock
        mock_session.close = AsyncMock

        mock_ctx = MagicMock
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("database.async_session", return_value=mock_ctx):
            gen = get_db
            session = await gen.__anext__
            assert session is mock_session
            try:
                await gen.athrow(RuntimeError("db error"))
            except RuntimeError:
                pass
            mock_session.rollback.assert_awaited

    @pytest.mark.asyncio
    async def test_get_db_commits_on_normal_exit(self):
        """get_db should commit after the consumer completes without error."""
        from database import get_db

        mock_session = AsyncMock
        mock_session.commit = AsyncMock
        mock_session.rollback = AsyncMock
        mock_session.close = AsyncMock

        mock_ctx = MagicMock
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("database.async_session", return_value=mock_ctx):
            gen = get_db
            session = await gen.__anext__
            assert session is mock_session
            # Drive the generator to completion (normal path → commit)
            try:
                await gen.__anext__
            except StopAsyncIteration:
                pass
            mock_session.commit.assert_awaited_once

    @pytest.mark.asyncio
    async def test_get_db_close_called_on_exception(self):
        """get_db should call session.close in finally even on error."""
        from database import get_db

        mock_session = AsyncMock
        mock_session.commit = AsyncMock
        mock_session.rollback = AsyncMock
        mock_session.close = AsyncMock

        mock_ctx = MagicMock
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("database.async_session", return_value=mock_ctx):
            gen = get_db
            await gen.__anext__
            try:
                await gen.athrow(ValueError("forced failure"))
            except ValueError:
                pass
            mock_session.close.assert_awaited

    @pytest.mark.asyncio
    async def test_get_db_close_called_on_normal_exit(self):
        """get_db should call session.close in finally on clean exit."""
        from database import get_db

        mock_session = AsyncMock
        mock_session.commit = AsyncMock
        mock_session.rollback = AsyncMock
        mock_session.close = AsyncMock

        mock_ctx = MagicMock
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("database.async_session", return_value=mock_ctx):
            gen = get_db
            await gen.__anext__
            try:
                await gen.__anext__
            except StopAsyncIteration:
                pass
            mock_session.close.assert_awaited


class TestInitDb:
    """Test init_db table-creation logic."""

    @pytest.mark.asyncio
    async def test_init_db_calls_create_all(self):
        """init_db should call Base.metadata.create_all via run_sync."""
        from database import init_db, Base

        mock_conn = AsyncMock
        mock_conn.run_sync = AsyncMock

        mock_begin_ctx = MagicMock
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock
        mock_engine.begin = MagicMock(return_value=mock_begin_ctx)

        with patch("database.engine", mock_engine):
            await init_db

        # Verify run_sync was called with Base.metadata.create_all
        mock_conn.run_sync.assert_awaited_once_with(Base.metadata.create_all)

    @pytest.mark.asyncio
    async def test_init_db_uses_begin_context(self):
        """init_db should use engine.begin as an async context manager."""
        from database import init_db

        mock_conn = AsyncMock
        mock_conn.run_sync = AsyncMock

        begin_entered = []

        mock_begin_ctx = MagicMock
        mock_begin_ctx.__aenter__ = AsyncMock(
            side_effect=lambda: begin_entered.append(True) or mock_conn
        )
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock
        mock_engine.begin = MagicMock(return_value=mock_begin_ctx)

        with patch("database.engine", mock_engine):
            await init_db

        assert len(begin_entered) == 1
        mock_engine.begin.assert_called_once
