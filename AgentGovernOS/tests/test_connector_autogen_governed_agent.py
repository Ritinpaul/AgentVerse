"""
Unit tests for the AutoGen connector (governed_agent.py).

Tests:
    - GovernedAssistantAgent wrapping
    - GovernedUserProxyAgent wrapping
    - generate_reply and initiate_chat authorization
    - Governance approval and denial flows
"""

from unittest.mock import MagicMock, patch

import pytest

from connectors.autogen.governed_agent import (
    GovernedAssistantAgent,
    GovernedUserProxyAgent,
)
from connectors.sdk.govcore import GovernanceVerdict


class TestGovernedAssistantAgent:
    """Test the GovernedAssistantAgent wrapper."""

    def test_agent_initialization(self):
        """Test GovernedAssistantAgent initialization."""
        mock_agent = MagicMock

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="CODE-ASSISTANT-001",
            calling_system="VSCode",
        )

        assert gov_agent.agent_code == "CODE-ASSISTANT-001"
        assert gov_agent.calling_system == "VSCode"
        assert gov_agent._agent is mock_agent

    def test_generate_reply_approved(self):
        """Test generate_reply when governance APPROVES."""
        mock_agent = MagicMock
        mock_agent.generate_reply.return_value = "Here's the code you requested..."

        mock_sender = MagicMock
        mock_sender.name = "user_proxy"

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="CODE-ASSISTANT-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="LOW",
            )

            messages = [
                {"role": "user", "content": "Write a Python function to sort a list"},
            ]

            result = gov_agent.generate_reply(messages=messages, sender=mock_sender)

            # Verify governance was called
            mock_evaluate.assert_called_once
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "CODE-ASSISTANT-001"
            assert envelope.agent_source == "autogen"
            assert "generate_reply:" in envelope.action_requested
            assert envelope.context["message_count"] == 1
            assert "sort a list" in envelope.context["last_message_preview"]
            assert envelope.context["sender"] == "user_proxy"

            # Verify agent.generate_reply was called
            mock_agent.generate_reply.assert_called_once
            assert "code you requested" in result

    def test_generate_reply_blocked(self):
        """Test generate_reply when governance BLOCKS."""
        mock_agent = MagicMock

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="CODE-ASSISTANT-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                risk_score="HIGH",
                reason="Code generation blocked: security policy violation",
            )

            messages = [
                {"role": "user", "content": "Write malicious code"},
            ]

            result = gov_agent.generate_reply(messages=messages)

            # Verify agent.generate_reply was NOT called
            mock_agent.generate_reply.assert_not_called

            # Verify blocked message is returned
            assert "BLOCKED by AgentGovern" in result
            assert "security policy violation" in result

    def test_generate_reply_without_messages(self):
        """Test generate_reply when messages is None."""
        mock_agent = MagicMock
        mock_agent.generate_reply.return_value = "Hello"

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="TEST-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            result = gov_agent.generate_reply(messages=None)

            # Verify it handles None messages
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.context["message_count"] == 0

    def test_generate_reply_with_sender_without_name(self):
        """Test generate_reply when sender has no name attribute."""
        mock_agent = MagicMock
        mock_agent.generate_reply.return_value = "Response"

        mock_sender = "simple_string_sender"

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="TEST-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            gov_agent.generate_reply(messages=[{"content": "hi"}], sender=mock_sender)

            envelope = mock_evaluate.call_args[0][0]
            assert envelope.context["sender"] == "simple_string_sender"

    def test_initiate_chat_approved(self):
        """Test initiate_chat when governance APPROVES."""
        mock_agent = MagicMock
        mock_agent.initiate_chat.return_value = {"status": "chat_completed"}

        mock_recipient = MagicMock
        mock_recipient.name = "assistant"

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="USER-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            result = gov_agent.initiate_chat(
                recipient=mock_recipient,
                message="Let's solve this problem",
            )

            # Verify governance was called
            mock_evaluate.assert_called_once
            envelope = mock_evaluate.call_args[0][0]
            assert "initiate_chat:" in envelope.action_requested
            assert envelope.context["recipient"] == "assistant"
            assert "solve this problem" in envelope.context["initial_message"]

            # Verify initiate_chat was called
            mock_agent.initiate_chat.assert_called_once
            assert result == {"status": "chat_completed"}

    def test_initiate_chat_blocked(self):
        """Test initiate_chat when governance BLOCKS."""
        mock_agent = MagicMock
        mock_recipient = MagicMock

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="USER-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                reason="Chat initiation denied",
            )

            with pytest.raises(PermissionError) as exc_info:
                gov_agent.initiate_chat(
                    recipient=mock_recipient,
                    message="Unauthorized action",
                )

            assert "Chat blocked" in str(exc_info.value)

            # Verify initiate_chat was NOT called
            mock_agent.initiate_chat.assert_not_called

    def test_attribute_passthrough(self):
        """Test that GovernedAssistantAgent passes through attributes."""
        mock_agent = MagicMock
        mock_agent.name = "coding_agent"
        mock_agent.llm_config = {"model": "gpt-4o"}
        mock_agent.custom_method.return_value = "test_value"

        gov_agent = GovernedAssistantAgent(
            agent=mock_agent,
            agent_code="TEST-001",
        )

        assert gov_agent.name == "coding_agent"
        assert gov_agent.llm_config == {"model": "gpt-4o"}
        assert gov_agent.custom_method == "test_value"


class TestGovernedUserProxyAgent:
    """Test the GovernedUserProxyAgent wrapper."""

    def test_proxy_agent_initialization(self):
        """Test GovernedUserProxyAgent initialization."""
        mock_agent = MagicMock

        gov_agent = GovernedUserProxyAgent(
            agent=mock_agent,
            agent_code="PROXY-001",
            calling_system="Terminal",
        )

        assert gov_agent.agent_code == "PROXY-001"
        assert gov_agent.calling_system == "Terminal"
        assert gov_agent._agent is mock_agent

    def test_proxy_initiate_chat_approved(self):
        """Test proxy initiate_chat when governance APPROVES."""
        mock_agent = MagicMock
        mock_agent.initiate_chat.return_value = {"status": "completed"}

        mock_recipient = MagicMock
        mock_recipient.name = "assistant"

        gov_agent = GovernedUserProxyAgent(
            agent=mock_agent,
            agent_code="PROXY-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            result = gov_agent.initiate_chat(
                recipient=mock_recipient,
                message="Execute code to analyze data",
            )

            # Verify governance was called
            mock_evaluate.assert_called_once
            envelope = mock_evaluate.call_args[0][0]
            assert "proxy_initiate_chat:" in envelope.action_requested
            assert envelope.context["recipient"] == "assistant"
            assert "analyze data" in envelope.context["message"]

            # Verify initiate_chat was called
            mock_agent.initiate_chat.assert_called_once
            assert result == {"status": "completed"}

    def test_proxy_initiate_chat_blocked(self):
        """Test proxy initiate_chat when governance BLOCKS."""
        mock_agent = MagicMock
        mock_recipient = MagicMock

        gov_agent = GovernedUserProxyAgent(
            agent=mock_agent,
            agent_code="PROXY-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                reason="Code execution denied",
            )

            with pytest.raises(PermissionError) as exc_info:
                gov_agent.initiate_chat(
                    recipient=mock_recipient,
                    message="Execute system command",
                )

            assert "Proxy chat blocked" in str(exc_info.value)

            # Verify initiate_chat was NOT called
            mock_agent.initiate_chat.assert_not_called

    def test_proxy_attribute_passthrough(self):
        """Test that GovernedUserProxyAgent passes through attributes."""
        mock_agent = MagicMock
        mock_agent.name = "user_proxy"
        mock_agent.code_execution_config = {"work_dir": "/tmp"}

        gov_agent = GovernedUserProxyAgent(
            agent=mock_agent,
            agent_code="PROXY-001",
        )

        assert gov_agent.name == "user_proxy"
        assert gov_agent.code_execution_config == {"work_dir": "/tmp"}


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_multi_agent_conversation(self):
        """Test a multi-agent conversation with governance."""
        mock_assistant = MagicMock
        mock_assistant.generate_reply.return_value = "I'll help you with that code."

        mock_sender = MagicMock
        mock_sender.name = "user_proxy"

        gov_assistant = GovernedAssistantAgent(
            agent=mock_assistant,
            agent_code="DEV-BOT-001",
            calling_system="VSCode",
        )

        with patch.object(gov_assistant._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="LOW",
                audit_id="AUD-999",
            )

            messages = [
                {"role": "user", "content": "Write a function to validate email addresses"},
                {"role": "assistant", "content": "I can help with that."},
                {"role": "user", "content": "Make it TypeScript compatible"},
            ]

            result = gov_assistant.generate_reply(messages=messages, sender=mock_sender)

            # Verify governance context
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "DEV-BOT-001"
            assert envelope.calling_system == "VSCode"
            assert envelope.context["message_count"] == 3
            assert "TypeScript" in envelope.context["last_message_preview"]

            # Verify response
            assert "help you with that code" in result

    def test_code_execution_governance(self):
        """Test governance for code execution via UserProxyAgent."""
        mock_proxy = MagicMock
        mock_proxy.initiate_chat.return_value = {"output": "Code executed"}

        mock_assistant = MagicMock
        mock_assistant.name = "coder"

        gov_proxy = GovernedUserProxyAgent(
            agent=mock_proxy,
            agent_code="EXEC-PROXY-001",
            calling_system="Notebook",
        )

        with patch.object(gov_proxy._gov, "evaluate") as mock_evaluate:
            # Simulate ESCALATED verdict for code execution
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="ESCALATED",
                approved=False,
                requires_human_review=True,
                reason="Code execution requires human approval",
            )

            with pytest.raises(PermissionError) as exc_info:
                gov_proxy.initiate_chat(
                    recipient=mock_assistant,
                    message="import os; os.system('rm -rf /')",
                )

            assert "Proxy chat blocked" in str(exc_info.value)
            mock_proxy.initiate_chat.assert_not_called
