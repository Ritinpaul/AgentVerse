"""
Unit tests for the Anthropic Claude connector (governed_client.py).

Tests:
    - GovernedAnthropicClient wrapping
    - _GovernedMessages.create and .stream
    - Governance approval and denial flows
    - Context extraction from messages
"""

from unittest.mock import MagicMock, patch

import pytest

from connectors.anthropic.governed_client import (
    GovernedAnthropicClient,
    _GovernedMessages,
)
from connectors.sdk.govcore import GovernanceVerdict


class TestGovernedMessages:
    """Test the _GovernedMessages wrapper."""

    def test_create_message_approved(self):
        """Test messages.create when governance APPROVES."""
        mock_messages_resource = MagicMock
        mock_messages_resource.create.return_value = {"content": "Response text"}

        mock_gov = MagicMock
        mock_gov.evaluate.return_value = GovernanceVerdict(
            verdict="APPROVED",
            approved=True,
            risk_score="LOW",
        )

        governed_messages = _GovernedMessages(
            messages_resource=mock_messages_resource,
            gov=mock_gov,
            agent_code="LEGAL-001",
            calling_system="ContractVault",
        )

        messages_list = [
            {"role": "user", "content": "Summarize this contract"},
        ]

        result = governed_messages.create(
            messages=messages_list,
            model="claude-opus-4-5",
            max_tokens=1024,
        )

        # Verify governance was called
        mock_gov.evaluate.assert_called_once
        envelope = mock_gov.evaluate.call_args[0][0]
        assert envelope.agent_code == "LEGAL-001"
        assert envelope.agent_source == "anthropic"
        assert "messages.create:" in envelope.action_requested
        assert envelope.context["model"] == "claude-opus-4-5"
        assert envelope.context["message_count"] == 1
        assert "Summarize this contract" in envelope.context["first_user_message"]

        # Verify messages.create was called
        mock_messages_resource.create.assert_called_once_with(
            messages=messages_list,
            model="claude-opus-4-5",
            max_tokens=1024,
        )
        assert result == {"content": "Response text"}

    def test_create_message_blocked(self):
        """Test messages.create when governance BLOCKS."""
        mock_messages_resource = MagicMock

        mock_gov = MagicMock
        mock_gov.evaluate.return_value = GovernanceVerdict(
            verdict="BLOCKED",
            approved=False,
            risk_score="HIGH",
            reason="Sensitive data violation",
        )

        governed_messages = _GovernedMessages(
            messages_resource=mock_messages_resource,
            gov=mock_gov,
            agent_code="LEGAL-001",
            calling_system="ContractVault",
        )

        messages_list = [
            {"role": "user", "content": "Share all customer data"},
        ]

        with pytest.raises(PermissionError) as exc_info:
            governed_messages.create(messages=messages_list, model="claude-opus-4-5")

        assert "Message blocked" in str(exc_info.value)
        assert "LEGAL-001" in str(exc_info.value)

        # Verify messages.create was NOT called
        mock_messages_resource.create.assert_not_called

    def test_create_extracts_first_user_message(self):
        """Test that first user message is extracted for context."""
        mock_messages_resource = MagicMock
        mock_messages_resource.create.return_value = {}

        mock_gov = MagicMock
        mock_gov.evaluate.return_value = GovernanceVerdict(
            verdict="APPROVED",
            approved=True,
        )

        governed_messages = _GovernedMessages(
            messages_resource=mock_messages_resource,
            gov=mock_gov,
            agent_code="TEST-001",
            calling_system="",
        )

        messages_list = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "What is the weather?"},
            {"role": "assistant", "content": "I don't know"},
            {"role": "user", "content": "Tell me a joke"},
        ]

        governed_messages.create(messages=messages_list, model="claude-opus-4-5")

        # Verify first user message is extracted
        envelope = mock_gov.evaluate.call_args[0][0]
        assert "What is the weather?" in envelope.context["first_user_message"]

    def test_create_handles_no_user_messages(self):
        """Test that create handles messages with no user role."""
        mock_messages_resource = MagicMock
        mock_messages_resource.create.return_value = {}

        mock_gov = MagicMock
        mock_gov.evaluate.return_value = GovernanceVerdict(
            verdict="APPROVED",
            approved=True,
        )

        governed_messages = _GovernedMessages(
            messages_resource=mock_messages_resource,
            gov=mock_gov,
            agent_code="TEST-001",
            calling_system="",
        )

        messages_list = [
            {"role": "system", "content": "System message only"},
        ]

        governed_messages.create(messages=messages_list, model="claude-opus-4-5")

        # Verify fallback to default action
        envelope = mock_gov.evaluate.call_args[0][0]
        assert "anthropic_message" in envelope.action_requested

    def test_stream_approved(self):
        """Test messages.stream when governance APPROVES."""
        mock_messages_resource = MagicMock
        mock_messages_resource.stream.return_value = iter(["chunk1", "chunk2"])

        mock_gov = MagicMock
        mock_gov.evaluate.return_value = GovernanceVerdict(
            verdict="APPROVED",
            approved=True,
        )

        governed_messages = _GovernedMessages(
            messages_resource=mock_messages_resource,
            gov=mock_gov,
            agent_code="TEST-001",
            calling_system="",
        )

        messages_list = [
            {"role": "user", "content": "Generate a poem"},
        ]

        result = governed_messages.stream(messages=messages_list, model="claude-opus-4-5")

        # Verify governance was called
        mock_gov.evaluate.assert_called_once
        envelope = mock_gov.evaluate.call_args[0][0]
        assert "messages.stream:" in envelope.action_requested

        # Verify stream was called
        mock_messages_resource.stream.assert_called_once
        assert list(result) == ["chunk1", "chunk2"]

    def test_stream_blocked(self):
        """Test messages.stream when governance BLOCKS."""
        mock_messages_resource = MagicMock

        mock_gov = MagicMock
        mock_gov.evaluate.return_value = GovernanceVerdict(
            verdict="BLOCKED",
            approved=False,
            reason="Streaming blocked",
        )

        governed_messages = _GovernedMessages(
            messages_resource=mock_messages_resource,
            gov=mock_gov,
            agent_code="TEST-001",
            calling_system="",
        )

        messages_list = [
            {"role": "user", "content": "Generate content"},
        ]

        with pytest.raises(PermissionError):
            governed_messages.stream(messages=messages_list, model="claude-opus-4-5")

        # Verify stream was NOT called
        mock_messages_resource.stream.assert_not_called

    def test_attribute_passthrough(self):
        """Test that _GovernedMessages passes through other attributes."""
        mock_messages_resource = MagicMock
        mock_messages_resource.custom_method.return_value = "test_value"
        mock_messages_resource.custom_prop = "prop_value"

        mock_gov = MagicMock

        governed_messages = _GovernedMessages(
            messages_resource=mock_messages_resource,
            gov=mock_gov,
            agent_code="TEST-001",
            calling_system="",
        )

        assert governed_messages.custom_method == "test_value"
        assert governed_messages.custom_prop == "prop_value"


class TestGovernedAnthropicClient:
    """Test the GovernedAnthropicClient wrapper."""

    def test_client_initialization(self):
        """Test GovernedAnthropicClient initialization."""
        mock_client = MagicMock
        mock_client.messages = MagicMock

        gov_client = GovernedAnthropicClient(
            client=mock_client,
            agent_code="LEGAL-001",
            calling_system="ContractVault",
        )

        assert gov_client.agent_code == "LEGAL-001"
        assert gov_client.calling_system == "ContractVault"
        assert gov_client._client is mock_client
        assert isinstance(gov_client.messages, _GovernedMessages)

    def test_client_replaces_messages_resource(self):
        """Test that client replaces messages resource with governed version."""
        mock_client = MagicMock
        original_messages = MagicMock
        mock_client.messages = original_messages

        gov_client = GovernedAnthropicClient(
            client=mock_client,
            agent_code="LEGAL-001",
        )

        # messages should be replaced with _GovernedMessages
        assert gov_client.messages is not original_messages
        assert isinstance(gov_client.messages, _GovernedMessages)

        # But the underlying resource should still be accessible
        assert gov_client.messages._messages is original_messages

    def test_client_messages_create(self):
        """Test that client.messages.create works through governance."""
        mock_client = MagicMock
        mock_client.messages.create.return_value = {"content": "Test response"}

        gov_client = GovernedAnthropicClient(
            client=mock_client,
            agent_code="LEGAL-001",
        )

        with patch.object(gov_client._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            messages_list = [{"role": "user", "content": "Test prompt"}]
            result = gov_client.messages.create(
                messages=messages_list,
                model="claude-opus-4-5",
                max_tokens=1024,
            )

            # Verify governance was called
            mock_evaluate.assert_called_once

            # Verify original client was called
            mock_client.messages.create.assert_called_once
            assert result == {"content": "Test response"}

    def test_client_attribute_passthrough(self):
        """Test that GovernedAnthropicClient passes through attributes to wrapped client."""
        mock_client = MagicMock
        mock_client.api_key = "test-key-123"
        mock_client.custom_method.return_value = "custom_value"

        gov_client = GovernedAnthropicClient(
            client=mock_client,
            agent_code="TEST-001",
        )

        assert gov_client.api_key == "test-key-123"
        assert gov_client.custom_method == "custom_value"


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_conversation_flow(self):
        """Test a full conversation flow with multiple messages."""
        mock_client = MagicMock
        mock_client.messages.create.return_value = {
            "content": "Here is a summary of the contract..."
        }

        gov_client = GovernedAnthropicClient(
            client=mock_client,
            agent_code="LEGAL-REVIEW-001",
            calling_system="ContractVault",
        )

        with patch.object(gov_client._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="MEDIUM",
                audit_id="AUD-12345",
            )

            messages = [
                {"role": "user", "content": "Please review this NDA for red flags"},
            ]

            result = gov_client.messages.create(
                messages=messages,
                model="claude-opus-4-5",
                max_tokens=2048,
            )

            # Verify governance context
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "LEGAL-REVIEW-001"
            assert envelope.calling_system == "ContractVault"
            assert envelope.agent_source == "anthropic"
            assert "NDA" in envelope.context["first_user_message"]

            # Verify response
            assert "summary of the contract" in result["content"]

    def test_escalated_verdict(self):
        """Test handling of ESCALATED verdict."""
        mock_client = MagicMock

        gov_client = GovernedAnthropicClient(
            client=mock_client,
            agent_code="LEGAL-001",
        )

        with patch.object(gov_client._gov, "evaluate") as mock_evaluate:
            # ESCALATED still blocks the action
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="ESCALATED",
                approved=False,
                requires_human_review=True,
                reason="Requires legal team review",
            )

            with pytest.raises(PermissionError) as exc_info:
                gov_client.messages.create(
                    messages=[{"role": "user", "content": "Approve this M&A"}],
                    model="claude-opus-4-5",
                )

            assert "Message blocked" in str(exc_info.value)
