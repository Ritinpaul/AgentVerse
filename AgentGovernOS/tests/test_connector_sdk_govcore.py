"""
Unit tests for the SDK Core (govcore.py).

Tests:
    - GovernanceEnvelope data model
    - GovernanceVerdict construction and offline modes
    - GovCore.evaluate with mocked HTTP calls
    - Fail-open and fail-safe behaviors
    - Health check endpoint
"""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from connectors.sdk.govcore import (
    DEFAULT_SERVER,
    GovCore,
    GovernanceEnvelope,
    GovernanceVerdict,
    evaluate,
    get_default_core,
)


class TestGovernanceEnvelope:
    """Test the GovernanceEnvelope data model."""

    def test_envelope_creation_with_defaults(self):
        """Test envelope creation with minimal fields."""
        envelope = GovernanceEnvelope(
            agent_code="TEST-001",
            action_requested="test_action",
        )
        assert envelope.agent_code == "TEST-001"
        assert envelope.action_requested == "test_action"
        assert envelope.agent_source == "unknown"
        assert envelope.session_id  # Auto-generated UUID
        assert envelope.context == {}

    def test_envelope_to_dict(self):
        """Test envelope serialization to dict."""
        envelope = GovernanceEnvelope(
            agent_code="TEST-001",
            action_requested="test_action",
            agent_source="pytest",
            context={"key": "value"},
            calling_system="TestSystem",
        )
        data = envelope.to_dict

        assert data["agent_code"] == "TEST-001"
        assert data["action_requested"] == "test_action"
        assert data["agent_source"] == "pytest"
        assert data["context"] == {"key": "value"}
        assert data["calling_system"] == "TestSystem"
        assert "timestamp" in data
        assert "sdk_version" in data
        assert data["session_id"]


class TestGovernanceVerdict:
    """Test the GovernanceVerdict data model."""

    def test_verdict_creation(self):
        """Test verdict creation."""
        verdict = GovernanceVerdict(
            verdict="APPROVED",
            approved=True,
            risk_score="LOW",
            policy_matched="POL-001",
            audit_id="AUD-123",
            requires_human_review=False,
            reason="Pass",
        )
        assert verdict.verdict == "APPROVED"
        assert verdict.approved is True
        assert verdict.risk_score == "LOW"
        assert verdict.audit_id == "AUD-123"

    def test_approved_offline_verdict(self):
        """Test offline approved verdict (fail-open)."""
        verdict = GovernanceVerdict.approved_offline
        assert verdict.verdict == "APPROVED"
        assert verdict.approved is True
        assert verdict.mode == "offline"
        assert "fail-open" in verdict.reason.lower

    def test_blocked_offline_verdict(self):
        """Test offline blocked verdict (fail-safe)."""
        verdict = GovernanceVerdict.blocked_offline
        assert verdict.verdict == "BLOCKED"
        assert verdict.approved is False
        assert verdict.mode == "offline"
        assert "fail-safe" in verdict.reason.lower


class TestGovCore:
    """Test the GovCore evaluation engine."""

    def test_govcore_initialization_defaults(self):
        """Test GovCore uses environment variables by default."""
        with patch.dict(os.environ, {"AGENTGOVERN_SERVER": "https://custom.server"}):
            core = GovCore
            assert core.server == "https://custom.server"

    def test_govcore_initialization_explicit(self):
        """Test GovCore with explicit parameters."""
        core = GovCore(
            server="http://test.server:8080",
            api_key="test-key-123",
            fail_open=False,
        )
        assert core.server == "http://test.server:8080"
        assert core.api_key == "test-key-123"
        assert core.fail_open is False

    def test_evaluate_approved_response(self):
        """Test successful evaluation with APPROVED verdict."""
        core = GovCore(server="http://test.server")
        envelope = GovernanceEnvelope(
            agent_code="TEST-001",
            action_requested="safe_action",
        )

        mock_response = MagicMock
        mock_response.json.return_value = {
            "verdict": "APPROVED",
            "risk_score": "LOW",
            "policy_matched": "POL-001",
            "audit_id": "AUD-123",
            "requires_human_review": False,
            "reason": "Policy allows action",
        }
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            verdict = core.evaluate(envelope)

            assert verdict.verdict == "APPROVED"
            assert verdict.approved is True
            assert verdict.risk_score == "LOW"
            assert verdict.audit_id == "AUD-123"
            assert verdict.mode == "online"

    def test_evaluate_blocked_response(self):
        """Test evaluation with BLOCKED verdict."""
        core = GovCore(server="http://test.server")
        envelope = GovernanceEnvelope(
            agent_code="TEST-001",
            action_requested="risky_action",
        )

        mock_response = MagicMock
        mock_response.json.return_value = {
            "verdict": "BLOCKED",
            "risk_score": "HIGH",
            "reason": "Policy violation",
        }
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            verdict = core.evaluate(envelope)

            assert verdict.verdict == "BLOCKED"
            assert verdict.approved is False
            assert verdict.risk_score == "HIGH"

    def test_evaluate_server_unreachable_fail_open(self):
        """Test fail-open behavior when server is unreachable."""
        core = GovCore(server="http://unreachable.server", fail_open=True)
        envelope = GovernanceEnvelope(
            agent_code="TEST-001",
            action_requested="test_action",
        )

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("Connection failed")

            verdict = core.evaluate(envelope)

            assert verdict.verdict == "APPROVED"
            assert verdict.approved is True
            assert verdict.mode == "offline"
            assert "fail-open" in verdict.reason.lower

    def test_evaluate_server_unreachable_fail_safe(self):
        """Test fail-safe behavior when server is unreachable."""
        core = GovCore(server="http://unreachable.server", fail_open=False)
        envelope = GovernanceEnvelope(
            agent_code="TEST-001",
            action_requested="test_action",
        )

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("Connection failed")

            verdict = core.evaluate(envelope)

            assert verdict.verdict == "BLOCKED"
            assert verdict.approved is False
            assert verdict.mode == "offline"
            assert "fail-safe" in verdict.reason.lower

    def test_evaluate_with_api_key_header(self):
        """Test that API key is sent in headers when provided."""
        core = GovCore(server="http://test.server", api_key="secret-key-123")
        envelope = GovernanceEnvelope(
            agent_code="TEST-001",
            action_requested="test_action",
        )

        mock_response = MagicMock
        mock_response.json.return_value = {"verdict": "APPROVED"}
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client:
            mock_post = mock_client.return_value.__enter__.return_value.post
            mock_post.return_value = mock_response

            core.evaluate(envelope)

            # Verify headers include API key
            call_kwargs = mock_post.call_args[1]
            assert "X-API-Key" in call_kwargs["headers"]
            assert call_kwargs["headers"]["X-API-Key"] == "secret-key-123"

    def test_is_reachable_success(self):
        """Test health check when server is reachable."""
        core = GovCore(server="http://test.server")

        mock_response = MagicMock
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            assert core.is_reachable is True

    def test_is_reachable_failure(self):
        """Test health check when server is unreachable."""
        core = GovCore(server="http://unreachable.server")

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")

            assert core.is_reachable is False


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_get_default_core_creates_singleton(self):
        """Test that get_default_core returns a singleton."""
        # Clear singleton
        import connectors.sdk.govcore as govcore_module
        govcore_module._default_core = None

        core1 = get_default_core
        core2 = get_default_core

        assert core1 is core2

    def test_evaluate_convenience_function(self):
        """Test module-level evaluate function."""
        mock_response = MagicMock
        mock_response.json.return_value = {"verdict": "APPROVED"}
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            verdict = evaluate(
                agent_code="TEST-001",
                action="test_action",
                agent_source="pytest",
                context={"key": "value"},
            )

            assert verdict.verdict == "APPROVED"
            assert verdict.approved is True


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def test_fail_open_environment_variable_true(self):
        """Test AGENTGOVERN_FAIL_OPEN=true."""
        with patch.dict(os.environ, {"AGENTGOVERN_FAIL_OPEN": "true"}):
            core = GovCore
            assert core.fail_open is True

    def test_fail_open_environment_variable_false(self):
        """Test AGENTGOVERN_FAIL_OPEN=false."""
        with patch.dict(os.environ, {"AGENTGOVERN_FAIL_OPEN": "false"}):
            core = GovCore
            assert core.fail_open is False

    def test_fail_open_default_is_true(self):
        """Test that fail_open defaults to True."""
        with patch.dict(os.environ, {}, clear=True):
            core = GovCore
            assert core.fail_open is True

    def test_server_default(self):
        """Test that server defaults to DEFAULT_SERVER."""
        with patch.dict(os.environ, {}, clear=True):
            core = GovCore
            assert core.server == DEFAULT_SERVER.rstrip("/")

    def test_api_key_from_environment(self):
        """Test API key loaded from environment."""
        with patch.dict(os.environ, {"AGENTGOVERN_API_KEY": "env-key-123"}):
            core = GovCore
            assert core.api_key == "env-key-123"
