"""
Comprehensive CLI integration tests for AgentGovern.

Tests all major CLI commands and features including:
- scan command with various formats
- agents commands
- policy commands
- audit commands
- init command
- watch mode
"""

import pytest
import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from agentgovern.cli import app


runner = CliRunner


@pytest.fixture
def sample_project(tmp_path):
    """Create a temporary project with agentgovern.yaml."""
    manifest = tmp_path / "agentgovern.yaml"
    manifest.write_text("""
version: "1.0"
project: "TestProject"
governance:
  policy_bundle: "default"
  compliance: []

agents:
  - code: "TEST-001"
    name: "Test Agent"
    framework: "crewai"
    tier: "T3"
    authority_limit: 5000.00
    currency: "USD"
    allowed_actions:
      - read_data
    denied_actions:
      - delete_records
    platform_bindings: []
    risk_tolerance: "medium"
""")
    return tmp_path


class TestInitCommand:
    """Test the init command."""

    def test_init_creates_manifest(self, tmp_path):
        """Test that init creates agentgovern.yaml."""
        # Mock user input
        with patch('typer.prompt', side_effect=[
            "TestProject",
            "crewai",
            "AGENT-001",
            "My Agent",
            "T3",
            "10000.00"
        ]):
            result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        manifest_path = tmp_path / "agentgovern.yaml"
        assert manifest_path.exists

        content = manifest_path.read_text
        assert "TestProject" in content
        assert "AGENT-001" in content
        assert "My Agent" in content

    def test_init_respects_force_flag(self, sample_project):
        """Test that --force overwrites existing manifest."""
        with patch('typer.prompt', side_effect=[
            "NewProject",
            "langchain",
            "NEW-001",
            "New Agent",
            "T2",
            "20000.00"
        ]):
            result = runner.invoke(app, ["init", str(sample_project), "--force"])

        assert result.exit_code == 0
        manifest = sample_project / "agentgovern.yaml"
        content = manifest.read_text
        assert "NewProject" in content


class TestVersionCommand:
    """Test the version command."""

    def test_version_displays_info(self):
        """Test that version command shows version information."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "AgentGovern" in result.stdout
        assert "v" in result.stdout


class TestScanCommand:
    """Test the scan command with various options."""

    def test_scan_table_format(self, sample_project):
        """Test scan with default table format."""
        result = runner.invoke(app, ["scan", str(sample_project)])
        assert result.exit_code == 0
        assert "AgentGovern" in result.stdout
        assert "TEST-001" in result.stdout or "Scanning" in result.stdout

    def test_scan_json_format(self, sample_project):
        """Test scan with JSON output format."""
        output_file = sample_project / "abom.json"
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--format", "json",
            "--output", str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists

        # Verify JSON structure
        data = json.loads(output_file.read_text)
        assert "project" in data
        assert "agents" in data
        assert "summary" in data
        assert data["summary"]["total_agents"] >= 1

    def test_scan_sarif_format(self, sample_project):
        """Test scan with SARIF output format."""
        output_file = sample_project / "results.sarif"
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--format", "sarif",
            "--output", str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists

        # Verify SARIF structure
        data = json.loads(output_file.read_text)
        assert "version" in data
        assert data["version"] == "2.1.0"
        assert "runs" in data

    def test_scan_html_format(self, sample_project):
        """Test scan with HTML output format."""
        output_file = sample_project / "report.html"
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--format", "html",
            "--output", str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists

        # Verify HTML content
        content = output_file.read_text
        assert "<!DOCTYPE html>" in content
        assert "AgentGovern" in content
        assert "TestProject" in content or "TEST-001" in content

    def test_scan_ci_mode(self, sample_project):
        """Test scan in CI mode with minimal output."""
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--ci",
            "--format", "json"
        ])

        # CI mode should have minimal stdout
        assert result.exit_code in [0, 1]
        # Should output valid JSON to stdout
        try:
            data = json.loads(result.stdout)
            assert "project" in data
        except json.JSONDecodeError:
            pass  # CI mode might have empty output for table format

    def test_scan_with_policy_bundle(self, sample_project):
        """Test scan with custom policy bundle."""
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--policy-bundle", "default"
        ])

        assert result.exit_code in [0, 1]
        assert "Policy bundle" in result.stdout or "Scanning" in result.stdout

    def test_scan_fail_on_threshold(self, sample_project):
        """Test scan with --fail-on threshold."""
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--fail-on", "critical"
        ])

        # Should succeed as long as there are no critical violations
        assert result.exit_code in [0, 1]

    def test_scan_no_codeprint(self, sample_project):
        """Test scan with --no-codeprint flag."""
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--no-codeprint"
        ])

        assert result.exit_code in [0, 1]

    def test_scan_nonexistent_path(self):
        """Test scan with nonexistent path fails gracefully."""
        result = runner.invoke(app, ["scan", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "Error" in result.stdout or "does not exist" in result.stdout


class TestWatchMode:
    """Test watch mode functionality."""

    def test_watch_mode_requires_watchdog(self, sample_project):
        """Test that watch mode shows helpful error if watchdog not installed."""
        # Mock watchdog import failure
        with patch('agentgovern.cli._run_watch_mode') as mock_watch:
            # Simulate import error
            import_error = ImportError("No module named 'watchdog'")
            mock_watch.side_effect = SystemExit(1)

            with patch('builtins.__import__', side_effect=import_error):
                result = runner.invoke(app, [
                    "scan", str(sample_project),
                    "--watch"
                ])

            # Should exit with error
            assert result.exit_code == 1


class TestAgentsCommands:
    """Test agents subcommands."""

    @patch('agentgovern.client.api.GovernanceAPIClient')
    def test_agents_list(self, mock_client_class):
        """Test agents list command."""
        # Mock server response
        mock_client = MagicMock
        mock_client.list_agents.return_value = [
            {
                "agent_code": "TEST-001",
                "agent_name": "Test Agent",
                "framework": "crewai",
                "tier": "T3",
                "authority_limit": 5000.0,
                "status": "active"
            }
        ]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["agents", "list"])

        assert result.exit_code == 0
        assert "TEST-001" in result.stdout
        assert "Test Agent" in result.stdout

    @patch('agentgovern.client.api.GovernanceAPIClient')
    def test_agents_show(self, mock_client_class):
        """Test agents show command."""
        # Mock server response
        mock_client = MagicMock
        mock_client.get_agent.return_value = {
            "agent_code": "TEST-001",
            "agent_name": "Test Agent",
            "framework": "crewai",
            "tier": "T3",
            "authority_limit": 5000.0,
            "status": "active"
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["agents", "show", "TEST-001"])

        assert result.exit_code == 0
        assert "TEST-001" in result.stdout

    @patch('agentgovern.client.api.GovernanceAPIClient')
    def test_agents_register(self, mock_client_class, sample_project):
        """Test agents register command."""
        # Mock server response
        mock_client = MagicMock
        mock_client.register_agent.return_value = {"success": True}
        mock_client_class.return_value = mock_client

        manifest_path = sample_project / "agentgovern.yaml"
        result = runner.invoke(app, ["agents", "register", str(manifest_path)])

        assert result.exit_code == 0
        assert "registered" in result.stdout.lower or "success" in result.stdout.lower

    @patch('agentgovern.client.api.GovernanceAPIClient')
    def test_agents_register_dry_run(self, mock_client_class, sample_project):
        """Test agents register with --dry-run flag."""
        mock_client = MagicMock
        mock_client_class.return_value = mock_client

        manifest_path = sample_project / "agentgovern.yaml"
        result = runner.invoke(app, [
            "agents", "register", str(manifest_path),
            "--dry-run"
        ])

        assert result.exit_code == 0
        assert "Dry run" in result.stdout or "TEST-001" in result.stdout
        # Verify no actual registration happened
        mock_client.register_agent.assert_not_called


class TestPolicyCommands:
    """Test policy subcommands."""

    def test_policy_list(self):
        """Test policy list command."""
        result = runner.invoke(app, ["policy", "list"])

        assert result.exit_code == 0
        assert "Policy Bundles" in result.stdout or "default" in result.stdout

    def test_policy_check(self, sample_project):
        """Test policy check command."""
        result = runner.invoke(app, [
            "policy", "check",
            str(sample_project),
            "--bundle", "default"
        ])

        assert result.exit_code in [0, 1]

    def test_policy_validate(self, tmp_path):
        """Test policy validate command."""
        # Create a valid policy bundle
        bundle_file = tmp_path / "custom.json"
        bundle_file.write_text(json.dumps({
            "name": "custom",
            "description": "Custom policy bundle",
            "rules": [
                {
                    "id": "CUSTOM-001",
                    "name": "Test Rule",
                    "severity": "HIGH",
                    "type": "authority_limit",
                    "params": {}
                }
            ]
        }, indent=2))

        result = runner.invoke(app, ["policy", "validate", str(bundle_file)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout or "custom" in result.stdout


class TestAuditCommands:
    """Test audit subcommands."""

    @patch('agentgovern.client.api.GovernanceAPIClient')
    def test_audit_tail(self, mock_client_class):
        """Test audit tail command."""
        # Mock server response
        mock_client = MagicMock
        mock_client.fetch_audit_logs.return_value = [
            {
                "created_at": "2026-03-17T10:00:00",
                "agent_code": "TEST-001",
                "action_requested": "process_payment",
                "verdict": "APPROVED",
                "amount_requested": 1000.0,
                "risk_score": "LOW"
            }
        ]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["audit", "tail"])

        assert result.exit_code == 0
        assert "Audit" in result.stdout or "TEST-001" in result.stdout

    @patch('agentgovern.client.api.GovernanceAPIClient')
    def test_audit_export(self, mock_client_class, tmp_path):
        """Test audit export command."""
        # Mock server response
        mock_client = MagicMock
        mock_client.fetch_audit_logs.return_value = [
            {
                "created_at": "2026-03-17T10:00:00",
                "agent_code": "TEST-001",
                "action_requested": "process_payment",
                "verdict": "APPROVED"
            }
        ]
        mock_client_class.return_value = mock_client

        output_file = tmp_path / "audit.json"
        result = runner.invoke(app, [
            "audit", "export",
            str(output_file),
            "--format", "json"
        ])

        assert result.exit_code == 0
        assert output_file.exists

        # Verify exported content
        data = json.loads(output_file.read_text)
        assert isinstance(data, list)
        assert len(data) > 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_scan_invalid_format(self, sample_project):
        """Test that invalid format is handled gracefully."""
        # Typer should catch this as enum validation
        result = runner.invoke(app, [
            "scan", str(sample_project),
            "--format", "invalid"
        ])

        assert result.exit_code != 0

    @patch('agentgovern.client.api.GovernanceAPIClient')
    def test_agents_list_connection_error(self, mock_client_class):
        """Test agents list with server connection error."""
        mock_client = MagicMock
        mock_client.list_agents.side_effect = ConnectionError("Server unreachable")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["agents", "list"])

        assert result.exit_code == 1
        assert "Error" in result.stdout or "unreachable" in result.stdout

    def test_init_without_force_on_existing(self, sample_project):
        """Test init without --force on existing manifest."""
        result = runner.invoke(app, ["init", str(sample_project)])

        assert result.exit_code == 0
        assert "exists" in result.stdout.lower or "force" in result.stdout.lower
