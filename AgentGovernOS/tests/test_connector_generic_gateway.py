"""
Unit tests for the Generic HTTP gateway connector (gateway.py).

Tests:
    - GovernanceGateway check and require methods
    - WebhookMiddleware event handling
    - governed_action decorator
    - Governance approval and denial flows
"""

from unittest.mock import MagicMock, patch

import pytest

from connectors.generic.gateway import (
    GovernanceGateway,
    WebhookMiddleware,
    governed_action,
)
from connectors.sdk.govcore import GovernanceVerdict


class TestGovernanceGateway:
    """Test the GovernanceGateway class."""

    def test_gateway_initialization(self):
        """Test GovernanceGateway initialization."""
        gateway = GovernanceGateway(
            agent_code="CUSTOM-BOT-001",
            calling_system="MyApp",
        )

        assert gateway.agent_code == "CUSTOM-BOT-001"
        assert gateway.calling_system == "MyApp"

    def test_check_approved(self):
        """Test check method when governance APPROVES."""
        gateway = GovernanceGateway(agent_code="TEST-001")

        with patch.object(gateway._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="LOW",
            )

            verdict = gateway.check(
                action="delete_user",
                context={"user_id": 42, "reason": "GDPR"},
            )

            # Verify governance was called
            mock_evaluate.assert_called_once
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "TEST-001"
            assert envelope.action_requested == "delete_user"
            assert envelope.agent_source == "generic"
            assert envelope.context == {"user_id": 42, "reason": "GDPR"}

            # Verify verdict
            assert verdict.approved is True
            assert verdict.verdict == "APPROVED"

    def test_check_blocked(self):
        """Test check method when governance BLOCKS."""
        gateway = GovernanceGateway(agent_code="TEST-001")

        with patch.object(gateway._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                risk_score="HIGH",
                reason="Unauthorized deletion",
            )

            verdict = gateway.check(
                action="delete_database",
                context={"database": "production"},
            )

            # Verify verdict
            assert verdict.approved is False
            assert verdict.verdict == "BLOCKED"
            assert verdict.reason == "Unauthorized deletion"

    def test_check_without_context(self):
        """Test check method without context."""
        gateway = GovernanceGateway(agent_code="TEST-001")

        with patch.object(gateway._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            verdict = gateway.check(action="ping")

            # Verify empty context is sent
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.context == {}

    def test_require_approved(self):
        """Test require method when governance APPROVES."""
        gateway = GovernanceGateway(agent_code="TEST-001")

        with patch.object(gateway._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            # Should not raise exception
            verdict = gateway.require(action="safe_action")
            assert verdict.approved is True

    def test_require_blocked(self):
        """Test require method when governance BLOCKS."""
        gateway = GovernanceGateway(agent_code="TEST-001")

        with patch.object(gateway._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                reason="Access denied",
            )

            # Should raise PermissionError
            with pytest.raises(PermissionError) as exc_info:
                gateway.require(action="dangerous_action")

            assert "dangerous_action" in str(exc_info.value)
            assert "Access denied" in str(exc_info.value)


class TestWebhookMiddleware:
    """Test the WebhookMiddleware class."""

    def test_middleware_initialization(self):
        """Test WebhookMiddleware initialization."""
        middleware = WebhookMiddleware(
            agent_code="SAP-AGENT-001",
            calling_system="SAP_BTP",
        )

        assert middleware.agent_code == "SAP-AGENT-001"
        assert middleware.action_key == "action"
        assert middleware.context_key == "context"

    def test_middleware_custom_keys(self):
        """Test WebhookMiddleware with custom action/context keys."""
        middleware = WebhookMiddleware(
            agent_code="TEST-001",
            action_key="event_type",
            context_key="payload",
        )

        assert middleware.action_key == "event_type"
        assert middleware.context_key == "payload"

    def test_handle_event_approved(self):
        """Test handle method when governance APPROVES."""
        middleware = WebhookMiddleware(agent_code="TEST-001")

        with patch.object(middleware._gw._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="LOW",
                audit_id="AUD-123",
            )

            event = {
                "action": "process_payment",
                "context": {"amount": 100, "currency": "USD"},
            }

            result = middleware.handle(event)

            # Verify result structure
            assert result["approved"] is True
            assert result["verdict"] == "APPROVED"
            assert result["risk_score"] == "LOW"
            assert result["audit_id"] == "AUD-123"
            assert result["requires_human_review"] is False
            assert result["mode"] == "online"

    def test_handle_event_blocked(self):
        """Test handle method when governance BLOCKS."""
        middleware = WebhookMiddleware(agent_code="TEST-001")

        with patch.object(middleware._gw._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                risk_score="HIGH",
                reason="Payment limit exceeded",
            )

            event = {
                "action": "process_payment",
                "context": {"amount": 1000000, "currency": "USD"},
            }

            result = middleware.handle(event)

            # Verify result structure
            assert result["approved"] is False
            assert result["verdict"] == "BLOCKED"
            assert result["risk_score"] == "HIGH"
            assert result["reason"] == "Payment limit exceeded"

    def test_handle_event_with_custom_keys(self):
        """Test handle with custom action/context keys."""
        middleware = WebhookMiddleware(
            agent_code="TEST-001",
            action_key="event_type",
            context_key="payload",
        )

        with patch.object(middleware._gw._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            event = {
                "event_type": "user_created",
                "payload": {"user_id": 42, "email": "test@example.com"},
            }

            middleware.handle(event)

            # Verify governance was called with correct action and context
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.action_requested == "user_created"
            assert envelope.context == {"user_id": 42, "email": "test@example.com"}

    def test_handle_event_with_type_fallback(self):
        """Test handle when 'action' key is missing, falls back to 'type'."""
        middleware = WebhookMiddleware(agent_code="TEST-001")

        with patch.object(middleware._gw._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            event = {
                "type": "webhook_event",
                "data": {"key": "value"},
            }

            middleware.handle(event)

            envelope = mock_evaluate.call_args[0][0]
            assert envelope.action_requested == "webhook_event"

    def test_handle_event_without_action_or_type(self):
        """Test handle when neither 'action' nor 'type' keys exist."""
        middleware = WebhookMiddleware(agent_code="TEST-001")

        with patch.object(middleware._gw._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            event = {
                "some_key": "some_value",
            }

            middleware.handle(event)

            envelope = mock_evaluate.call_args[0][0]
            assert envelope.action_requested == "unknown_action"

    def test_handle_event_context_includes_all_fields(self):
        """Test that context includes all event fields when context key is missing."""
        middleware = WebhookMiddleware(agent_code="TEST-001")

        with patch.object(middleware._gw._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            event = {
                "action": "process",
                "field1": "value1",
                "field2": "value2",
            }

            middleware.handle(event)

            envelope = mock_evaluate.call_args[0][0]
            # Context should include all fields except action
            assert envelope.context == {"field1": "value1", "field2": "value2"}


class TestGovernedActionDecorator:
    """Test the governed_action decorator."""

    def test_decorator_basic_usage(self):
        """Test decorator with basic function."""
        mock_gov = MagicMock

        with patch("connectors.generic.gateway.GovernanceGateway") as mock_gw_class:
            mock_gw_class.return_value.require.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            @governed_action(agent_code="FI-001", action="approve_payment")
            def approve_payment(amount: float, vendor: str):
                return {"status": "approved", "amount": amount, "vendor": vendor}

            result = approve_payment(5000.0, "VENDOR-001")

            # Verify function executed
            assert result == {"status": "approved", "amount": 5000.0, "vendor": "VENDOR-001"}

            # Verify governance was called
            mock_gw_class.return_value.require.assert_called_once

    def test_decorator_with_context_from_kwargs(self):
        """Test decorator extracts specified kwargs into context."""
        with patch("connectors.generic.gateway.GovernanceGateway") as mock_gw_class:
            mock_gw_class.return_value.require.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            @governed_action(
                agent_code="FI-001",
                action="approve_payment",
                context_from_kwargs=["amount", "currency"],
            )
            def approve_payment(amount: float, currency: str, vendor: str):
                return {"status": "approved"}

            approve_payment(amount=5000.0, currency="USD", vendor="VENDOR-001")

            # Verify context includes only specified kwargs
            call_args = mock_gw_class.return_value.require.call_args
            context = call_args[0][1]  # Second argument is context
            assert "amount" in context
            assert context["amount"] == 5000.0
            assert "currency" in context
            assert context["currency"] == "USD"
            # vendor should NOT be in context (not in context_from_kwargs)

    def test_decorator_with_positional_args(self):
        """Test decorator includes positional args in context."""
        with patch("connectors.generic.gateway.GovernanceGateway") as mock_gw_class:
            mock_gw_class.return_value.require.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            @governed_action(agent_code="TEST-001", action="process")
            def process_data(data1, data2):
                return "processed"

            process_data("value1", "value2")

            # Verify positional args are in context as arg0, arg1
            call_args = mock_gw_class.return_value.require.call_args
            context = call_args[0][1]
            assert "arg0" in context
            assert "arg1" in context

    def test_decorator_blocked_raises_exception(self):
        """Test decorator raises PermissionError when blocked."""
        with patch("connectors.generic.gateway.GovernanceGateway") as mock_gw_class:
            mock_gw_class.return_value.require.side_effect = PermissionError("Action denied")

            @governed_action(agent_code="FI-001", action="dangerous_action")
            def dangerous_function:
                return "should not execute"

            with pytest.raises(PermissionError) as exc_info:
                dangerous_function

            assert "Action denied" in str(exc_info.value)

    def test_decorator_uses_function_name_as_default_action(self):
        """Test decorator uses function name when action is not specified."""
        with patch("connectors.generic.gateway.GovernanceGateway") as mock_gw_class:
            mock_gw_class.return_value.require.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            @governed_action(agent_code="TEST-001")
            def my_custom_function:
                return "done"

            my_custom_function

            # Verify action uses function name
            call_args = mock_gw_class.return_value.require.call_args
            action = call_args[0][0]  # First argument is action
            assert action == "my_custom_function"

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""

        @governed_action(agent_code="TEST-001", action="test")
        def documented_function:
            """This is a documented function."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert "documented function" in documented_function.__doc__


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_webhook_flow(self):
        """Test a full webhook handling flow."""
        middleware = WebhookMiddleware(
            agent_code="SAP-AGENT-001",
            calling_system="SAP_BTP",
        )

        with patch.object(middleware._gw._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="MEDIUM",
                audit_id="AUD-789",
                policy_matched="POL-PAYMENT-001",
            )

            event = {
                "action": "approve_invoice",
                "context": {
                    "invoice_id": "INV-12345",
                    "amount": 25000,
                    "currency": "EUR",
                    "vendor": "VENDOR-001",
                },
            }

            result = middleware.handle(event)

            # Verify complete response
            assert result["approved"] is True
            assert result["verdict"] == "APPROVED"
            assert result["risk_score"] == "MEDIUM"
            assert result["audit_id"] == "AUD-789"

    def test_custom_agent_with_decorator(self):
        """Test custom agent function with decorator."""
        with patch("connectors.generic.gateway.GovernanceGateway") as mock_gw_class:
            mock_gw_class.return_value.require.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            @governed_action(
                agent_code="CUSTOM-AI-001",
                action="generate_report",
                calling_system="ReportingApp",
                context_from_kwargs=["report_type", "date_range"],
            )
            def generate_report(report_type: str, date_range: str, format: str = "PDF"):
                return {"report_id": "RPT-001", "status": "generated"}

            result = generate_report(
                report_type="financial",
                date_range="2024-Q1",
                format="PDF",
            )

            # Verify function executed
            assert result["report_id"] == "RPT-001"

            # Verify governance was called with correct params
            init_call = mock_gw_class.call_args
            assert init_call[1]["agent_code"] == "CUSTOM-AI-001"
            assert init_call[1]["calling_system"] == "ReportingApp"
