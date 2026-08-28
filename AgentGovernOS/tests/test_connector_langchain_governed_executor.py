"""
Unit tests for the LangChain connector (governed_executor.py).

Tests:
    - GovernedAgentExecutor invoke and stream methods
    - GovernedTool wrapping
    - Governance approval and denial flows
    - Context extraction and enrichment
"""

from unittest.mock import MagicMock, patch

import pytest

from connectors.langchain.governed_executor import (
    GovernedAgentExecutor,
    GovernedTool,
)
from connectors.sdk.govcore import GovernanceVerdict


class TestGovernedAgentExecutor:
    """Test the GovernedAgentExecutor wrapper."""

    def test_executor_initialization(self):
        """Test GovernedAgentExecutor initialization."""
        mock_executor = MagicMock

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="SUPPORT-BOT-001",
            calling_system="Zendesk",
        )

        assert gov_executor.agent_code == "SUPPORT-BOT-001"
        assert gov_executor.calling_system == "Zendesk"
        assert gov_executor._executor is mock_executor

    def test_invoke_approved(self):
        """Test invoke when governance APPROVES."""
        mock_executor = MagicMock
        mock_executor.invoke.return_value = {"output": "Refund processed"}

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="SUPPORT-BOT-001",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="LOW",
                audit_id="AUD-123",
            )

            inputs = {"input": "Issue refund of $150"}
            result = gov_executor.invoke(inputs)

            # Verify governance was called
            mock_evaluate.assert_called_once
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "SUPPORT-BOT-001"
            assert envelope.agent_source == "langchain"
            assert "llm_invoke:" in envelope.action_requested
            assert envelope.context["input"] == "Issue refund of $150"

            # Verify executor.invoke was called
            mock_executor.invoke.assert_called_once

            # Verify governance context is enriched in result
            assert result["output"] == "Refund processed"
            assert result["governance_verdict"] == "APPROVED"
            assert result["governance_audit_id"] == "AUD-123"

    def test_invoke_blocked(self):
        """Test invoke when governance BLOCKS."""
        mock_executor = MagicMock

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="SUPPORT-BOT-001",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                risk_score="HIGH",
                reason="Refund amount exceeds threshold",
                audit_id="AUD-456",
            )

            inputs = {"input": "Issue refund of $50,000"}
            result = gov_executor.invoke(inputs)

            # Verify executor.invoke was NOT called
            mock_executor.invoke.assert_not_called

            # Verify blocked response
            assert "BLOCKED by AgentGovern" in result["output"]
            assert "exceeds threshold" in result["output"]
            assert result["governance_verdict"] == "BLOCKED"
            assert result["governance_audit_id"] == "AUD-456"

    def test_invoke_extracts_input_from_dict(self):
        """Test that input is extracted from the inputs dict."""
        mock_executor = MagicMock
        mock_executor.invoke.return_value = {"output": "done"}

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="TEST-001",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            inputs = {
                "input": "Process this request",
                "additional_data": "extra context",
            }
            gov_executor.invoke(inputs)

            # Verify the full inputs dict is passed as context
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.context == inputs

    def test_invoke_with_kwargs(self):
        """Test invoke with additional kwargs."""
        mock_executor = MagicMock
        mock_executor.invoke.return_value = {"output": "done"}

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="TEST-001",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            inputs = {"input": "test"}
            gov_executor.invoke(inputs, max_iterations=5, verbose=True)

            # Verify kwargs are passed to executor
            mock_executor.invoke.assert_called_once_with(
                inputs,
                max_iterations=5,
                verbose=True,
            )

    def test_stream_approved(self):
        """Test stream when governance APPROVES."""
        mock_executor = MagicMock
        mock_executor.stream.return_value = iter([
            {"output": "chunk1"},
            {"output": "chunk2"},
        ])

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="TEST-001",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            inputs = {"input": "Generate report"}
            result = list(gov_executor.stream(inputs))

            # Verify stream was called
            mock_executor.stream.assert_called_once
            assert len(result) == 2
            assert result[0] == {"output": "chunk1"}

    def test_stream_blocked(self):
        """Test stream when governance BLOCKS."""
        mock_executor = MagicMock

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="TEST-001",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                reason="Streaming blocked",
            )

            inputs = {"input": "Stream data"}
            result = list(gov_executor.stream(inputs))

            # Verify stream was NOT called
            mock_executor.stream.assert_not_called

            # Verify blocked message
            assert len(result) == 1
            assert "BLOCKED by AgentGovern" in result[0]["output"]

    def test_attribute_passthrough(self):
        """Test that executor passes through attributes."""
        mock_executor = MagicMock
        mock_executor.agent_name = "Test Agent"
        mock_executor.custom_method.return_value = "test_value"

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="TEST-001",
        )

        assert gov_executor.agent_name == "Test Agent"
        assert gov_executor.custom_method == "test_value"


class TestGovernedTool:
    """Test the GovernedTool wrapper."""

    def test_tool_initialization(self):
        """Test GovernedTool initialization."""
        mock_tool = MagicMock
        mock_tool.name = "calculator"

        gov_tool = GovernedTool(
            tool=mock_tool,
            agent_code="MATH-001",
            calling_system="TestApp",
        )

        assert gov_tool.agent_code == "MATH-001"
        assert gov_tool.calling_system == "TestApp"
        assert gov_tool._tool is mock_tool

    def test_run_tool_approved(self):
        """Test tool run when governance APPROVES."""
        mock_tool = MagicMock
        mock_tool.name = "calculator"
        mock_tool.run.return_value = "42"

        gov_tool = GovernedTool(
            tool=mock_tool,
            agent_code="MATH-001",
        )

        with patch.object(gov_tool._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            result = gov_tool.run("2 + 2")

            # Verify governance was called
            mock_evaluate.assert_called_once
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "MATH-001"
            assert envelope.agent_source == "langchain"
            assert "tool:calculator" in envelope.action_requested
            assert "2 + 2" in envelope.context["tool_input"]

            # Verify tool.run was called
            mock_tool.run.assert_called_once_with("2 + 2")
            assert result == "42"

    def test_run_tool_blocked(self):
        """Test tool run when governance BLOCKS."""
        mock_tool = MagicMock
        mock_tool.name = "database_delete"

        gov_tool = GovernedTool(
            tool=mock_tool,
            agent_code="ADMIN-001",
        )

        with patch.object(gov_tool._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                reason="Unauthorized delete operation",
            )

            result = gov_tool.run("DELETE FROM users")

            # Verify tool.run was NOT called
            mock_tool.run.assert_not_called

            # Verify blocked message
            assert "BLOCKED by AgentGovern" in result
            assert "Tool 'tool:database_delete' denied" in result

    def test_run_tool_with_dict_input(self):
        """Test tool run with dictionary input."""
        mock_tool = MagicMock
        mock_tool.name = "api_caller"
        mock_tool.run.return_value = '{"status": "ok"}'

        gov_tool = GovernedTool(
            tool=mock_tool,
            agent_code="API-001",
        )

        with patch.object(gov_tool._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            tool_input = {"endpoint": "/users", "method": "GET"}
            result = gov_tool.run(tool_input, timeout=30)

            # Verify tool_input is stringified in context
            envelope = mock_evaluate.call_args[0][0]
            assert "endpoint" in envelope.context["tool_input"]

            # Verify kwargs are passed through
            mock_tool.run.assert_called_once_with(tool_input, timeout=30)

    def test_tool_attribute_passthrough(self):
        """Test that GovernedTool passes through attributes."""
        mock_tool = MagicMock
        mock_tool.name = "calculator"
        mock_tool.description = "Performs math calculations"
        mock_tool.custom_prop = "custom_value"

        gov_tool = GovernedTool(
            tool=mock_tool,
            agent_code="TEST-001",
        )

        assert gov_tool.name == "calculator"
        assert gov_tool.description == "Performs math calculations"
        assert gov_tool.custom_prop == "custom_value"

    def test_run_tool_handles_missing_name(self):
        """Test tool run when tool has no name attribute."""
        mock_tool = MagicMock(spec=[])  # No attributes
        mock_tool.run.return_value = "result"

        gov_tool = GovernedTool(
            tool=mock_tool,
            agent_code="TEST-001",
        )

        with patch.object(gov_tool._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            gov_tool.run("input")

            envelope = mock_evaluate.call_args[0][0]
            assert "tool:unknown" in envelope.action_requested


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_agent_workflow(self):
        """Test a full agent workflow with tools."""
        mock_executor = MagicMock
        mock_executor.invoke.return_value = {
            "output": "Customer refund of $200 has been processed",
            "intermediate_steps": [],
        }

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="SUPPORT-AGENT-001",
            calling_system="Zendesk",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="MEDIUM",
                audit_id="AUD-789",
                policy_matched="POL-REFUND-001",
            )

            inputs = {
                "input": "Process refund for customer #42, amount $200",
                "customer_id": "CUST-42",
                "amount": 200,
            }

            result = gov_executor.invoke(inputs)

            # Verify governance context
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "SUPPORT-AGENT-001"
            assert envelope.calling_system == "Zendesk"
            assert envelope.context == inputs

            # Verify result includes governance metadata
            assert "refund of $200" in result["output"]
            assert result["governance_verdict"] == "APPROVED"
            assert result["governance_audit_id"] == "AUD-789"

    def test_executor_with_non_dict_result(self):
        """Test executor when result is not a dict."""
        mock_executor = MagicMock
        # Some executors might return strings
        mock_executor.invoke.return_value = "Simple text output"

        gov_executor = GovernedAgentExecutor(
            executor=mock_executor,
            agent_code="TEST-001",
        )

        with patch.object(gov_executor._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            result = gov_executor.invoke({"input": "test"})

            # Non-dict results are returned as-is
            assert result == "Simple text output"
