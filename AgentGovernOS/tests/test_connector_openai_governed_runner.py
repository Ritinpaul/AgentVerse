"""
Unit tests for the OpenAI Agents SDK connector (governed_runner.py).

Tests:
    - GovernedRunner async and sync run methods
    - GovernedAgentWrapper
    - Governance approval and denial flows
    - Error handling and fail-open/fail-safe modes
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectors.openai.governed_runner import (
    GovernedAgentWrapper,
    GovernedRunner,
    govern_agent,
)
from connectors.sdk.govcore import GovernanceVerdict


class TestGovernedRunner:
    """Test the GovernedRunner wrapper."""

    def test_governed_runner_initialization(self):
        """Test GovernedRunner initialization."""
        runner = GovernedRunner(
            agent_code="SUPPORT-001",
            calling_system="Zendesk",
        )

        assert runner.agent_code == "SUPPORT-001"
        assert runner.calling_system == "Zendesk"

    @pytest.mark.asyncio
    async def test_run_async_approved(self):
        """Test async run when governance APPROVES."""
        runner = GovernedRunner(agent_code="SUPPORT-001")

        mock_agent = MagicMock
        mock_agent.name = "Support Agent"

        # Mock the openai-agents Runner
        with patch("connectors.openai.governed_runner.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(return_value={"output": "Processed successfully"})

            # Mock governance evaluation to approve
            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict(
                    verdict="APPROVED",
                    approved=True,
                    risk_score="LOW",
                )

                result = await runner.run(mock_agent, "Process refund for order #123")

                # Verify governance was called
                mock_evaluate.assert_called_once
                envelope = mock_evaluate.call_args[0][0]
                assert envelope.agent_code == "SUPPORT-001"
                assert envelope.agent_source == "openai_agents_sdk"
                assert "agents_sdk_run:" in envelope.action_requested
                assert envelope.context["input"] == "Process refund for order #123"

                # Verify Runner.run was called
                mock_runner_class.run.assert_awaited_once
                assert result == {"output": "Processed successfully"}

    @pytest.mark.asyncio
    async def test_run_async_blocked(self):
        """Test async run when governance BLOCKS."""
        runner = GovernedRunner(agent_code="SUPPORT-001")
        mock_agent = MagicMock

        with patch("connectors.openai.governed_runner.Runner") as mock_runner_class:
            # Mock governance evaluation to block
            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict(
                    verdict="BLOCKED",
                    approved=False,
                    risk_score="HIGH",
                    reason="Unauthorized refund amount",
                )

                with pytest.raises(PermissionError) as exc_info:
                    await runner.run(mock_agent, "Refund $1,000,000")

                assert "Action blocked" in str(exc_info.value)
                assert "SUPPORT-001" in str(exc_info.value)

                # Verify Runner.run was NOT called
                mock_runner_class.run.assert_not_called

    def test_run_sync_approved(self):
        """Test sync run when governance APPROVES."""
        runner = GovernedRunner(agent_code="SUPPORT-001")
        mock_agent = MagicMock
        mock_agent.name = "Support Agent"

        with patch("connectors.openai.governed_runner.Runner") as mock_runner_class:
            mock_runner_class.run_sync.return_value = {"output": "Processed"}

            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict(
                    verdict="APPROVED",
                    approved=True,
                )

                result = runner.run_sync(mock_agent, "Process return")

                # Verify governance was called
                mock_evaluate.assert_called_once
                envelope = mock_evaluate.call_args[0][0]
                assert "agents_sdk_run_sync:" in envelope.action_requested

                # Verify Runner.run_sync was called
                mock_runner_class.run_sync.assert_called_once
                assert result == {"output": "Processed"}

    def test_run_sync_blocked(self):
        """Test sync run when governance BLOCKS."""
        runner = GovernedRunner(agent_code="SUPPORT-001")
        mock_agent = MagicMock

        with patch("connectors.openai.governed_runner.Runner"):
            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict(
                    verdict="BLOCKED",
                    approved=False,
                    reason="Unauthorized action",
                )

                with pytest.raises(PermissionError):
                    runner.run_sync(mock_agent, "Delete all data")

    @pytest.mark.asyncio
    async def test_run_missing_openai_agents_package(self):
        """Test that ImportError is raised when openai-agents is not installed."""
        runner = GovernedRunner(agent_code="SUPPORT-001")
        mock_agent = MagicMock

        # Simulate ImportError when importing Runner
        with patch("connectors.openai.governed_runner.Runner", side_effect=ImportError):
            with pytest.raises(ImportError) as exc_info:
                await runner.run(mock_agent, "test")

            assert "openai-agents" in str(exc_info.value).lower


class TestGovernedAgentWrapper:
    """Test the GovernedAgentWrapper."""

    def test_wrapper_initialization(self):
        """Test GovernedAgentWrapper initialization."""
        mock_agent = MagicMock
        mock_agent.name = "Test Agent"

        wrapper = GovernedAgentWrapper(
            agent=mock_agent,
            agent_code="TEST-001",
            calling_system="TestSystem",
        )

        assert wrapper._agent is mock_agent
        assert wrapper.agent_code == "TEST-001"
        assert wrapper._runner.agent_code == "TEST-001"

    @pytest.mark.asyncio
    async def test_wrapper_run_async(self):
        """Test wrapper async run delegates to GovernedRunner."""
        mock_agent = MagicMock
        wrapper = GovernedAgentWrapper(agent=mock_agent, agent_code="TEST-001")

        with patch.object(wrapper._runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"result": "success"}

            result = await wrapper.run("test input", custom_param="value")

            mock_run.assert_awaited_once_with(mock_agent, "test input", custom_param="value")
            assert result == {"result": "success"}

    def test_wrapper_run_sync(self):
        """Test wrapper sync run delegates to GovernedRunner."""
        mock_agent = MagicMock
        wrapper = GovernedAgentWrapper(agent=mock_agent, agent_code="TEST-001")

        with patch.object(wrapper._runner, "run_sync") as mock_run_sync:
            mock_run_sync.return_value = {"result": "success"}

            result = wrapper.run_sync("test input", custom_param="value")

            mock_run_sync.assert_called_once_with(mock_agent, "test input", custom_param="value")
            assert result == {"result": "success"}

    def test_wrapper_attribute_passthrough(self):
        """Test that wrapper passes through attributes to wrapped agent."""
        mock_agent = MagicMock
        mock_agent.name = "Support Agent"
        mock_agent.custom_property = "test_value"

        wrapper = GovernedAgentWrapper(agent=mock_agent, agent_code="TEST-001")

        assert wrapper.name == "Support Agent"
        assert wrapper.custom_property == "test_value"


class TestGovernAgentFactory:
    """Test the govern_agent convenience factory."""

    def test_govern_agent_factory(self):
        """Test govern_agent factory creates GovernedAgentWrapper."""
        mock_agent = MagicMock

        wrapper = govern_agent(
            agent=mock_agent,
            agent_code="TEST-001",
            calling_system="TestSystem",
        )

        assert isinstance(wrapper, GovernedAgentWrapper)
        assert wrapper.agent_code == "TEST-001"


class TestContextExtraction:
    """Test that context is properly extracted and sent to governance."""

    @pytest.mark.asyncio
    async def test_run_extracts_agent_name_in_context(self):
        """Test that agent name is included in governance context."""
        runner = GovernedRunner(agent_code="SUPPORT-001")

        mock_agent = MagicMock
        mock_agent.name = "Customer Support Agent"

        with patch("connectors.openai.governed_runner.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(return_value={})

            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict(
                    verdict="APPROVED",
                    approved=True,
                )

                await runner.run(mock_agent, "Process request")

                envelope = mock_evaluate.call_args[0][0]
                assert envelope.context["agent_name"] == "Customer Support Agent"

    @pytest.mark.asyncio
    async def test_run_handles_agent_without_name(self):
        """Test that context handles agents without a name attribute."""
        runner = GovernedRunner(agent_code="SUPPORT-001")

        # Agent without name attribute
        mock_agent = MagicMock(spec=[])

        with patch("connectors.openai.governed_runner.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(return_value={})

            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict(
                    verdict="APPROVED",
                    approved=True,
                )

                await runner.run(mock_agent, "Process request")

                envelope = mock_evaluate.call_args[0][0]
                assert envelope.context["agent_name"] == "unknown"


class TestFailOpenBehavior:
    """Test fail-open and fail-safe behaviors."""

    @pytest.mark.asyncio
    async def test_runner_fail_open_on_server_error(self):
        """Test runner allows execution when server is unreachable (fail-open)."""
        runner = GovernedRunner(agent_code="TEST-001", fail_open=True)
        mock_agent = MagicMock

        with patch("connectors.openai.governed_runner.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(return_value={"result": "success"})

            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict.approved_offline

                result = await runner.run(mock_agent, "test")

                assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_runner_fail_safe_on_server_error(self):
        """Test runner blocks execution when server is unreachable (fail-safe)."""
        runner = GovernedRunner(agent_code="TEST-001", fail_open=False)
        mock_agent = MagicMock

        with patch("connectors.openai.governed_runner.Runner"):
            with patch.object(runner._gov, "evaluate") as mock_evaluate:
                mock_evaluate.return_value = GovernanceVerdict.blocked_offline

                with pytest.raises(PermissionError):
                    await runner.run(mock_agent, "test")
