"""
Unit tests for the CrewAI connector (governed_crew.py).

Tests:
    - GovernedAgent wrapping and authorization
    - GovernedCrew wrapping and kickoff authorization
    - Governance approval and denial flows
    - Error handling and fail-open/fail-safe modes
"""

from unittest.mock import MagicMock, patch

import pytest

from connectors.crewai.governed_crew import (
    GovernedAgent,
    GovernedCrew,
    govern_crew,
)
from connectors.sdk.govcore import GovernanceVerdict


class TestGovernedAgent:
    """Test the GovernedAgent wrapper."""

    def test_governed_agent_initialization(self):
        """Test GovernedAgent initialization."""
        mock_agent = MagicMock
        gov_agent = GovernedAgent(
            agent=mock_agent,
            agent_code="FI-ANALYST-001",
            calling_system="SAP_S4HANA",
        )

        assert gov_agent.agent_code == "FI-ANALYST-001"
        assert gov_agent.calling_system == "SAP_S4HANA"
        assert gov_agent._agent is mock_agent

    def test_execute_task_approved(self):
        """Test task execution when governance APPROVES."""
        mock_agent = MagicMock
        mock_agent.execute_task.return_value = {"result": "success"}

        mock_task = MagicMock
        mock_task.description = "Analyze financial data"

        gov_agent = GovernedAgent(
            agent=mock_agent,
            agent_code="FI-ANALYST-001",
        )

        # Mock the governance evaluation to approve
        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
                risk_score="LOW",
            )

            result = gov_agent.execute_task(mock_task, context={"amount": 1000})

            # Verify governance was called
            mock_evaluate.assert_called_once
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.agent_code == "FI-ANALYST-001"
            assert envelope.agent_source == "crewai"
            assert "execute_task:" in envelope.action_requested

            # Verify agent executed task
            mock_agent.execute_task.assert_called_once
            assert result == {"result": "success"}

    def test_execute_task_blocked(self):
        """Test task execution when governance BLOCKS."""
        mock_agent = MagicMock
        mock_task = MagicMock
        mock_task.description = "Delete all records"

        gov_agent = GovernedAgent(
            agent=mock_agent,
            agent_code="FI-ANALYST-001",
        )

        # Mock the governance evaluation to block
        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="BLOCKED",
                approved=False,
                risk_score="HIGH",
                reason="Policy violation: unauthorized action",
            )

            with pytest.raises(PermissionError) as exc_info:
                gov_agent.execute_task(mock_task)

            assert "Action blocked" in str(exc_info.value)
            assert "FI-ANALYST-001" in str(exc_info.value)

            # Verify agent was NOT called
            mock_agent.execute_task.assert_not_called

    def test_execute_task_with_context(self):
        """Test that context is passed to governance evaluation."""
        mock_agent = MagicMock
        mock_task = MagicMock
        mock_task.description = "Process payment"

        gov_agent = GovernedAgent(
            agent=mock_agent,
            agent_code="FI-ANALYST-001",
        )

        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            context = {"amount": 50000, "currency": "USD", "vendor": "VENDOR-001"}
            gov_agent.execute_task(mock_task, context=context)

            # Verify context was sent in the envelope
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.context == context

    def test_attribute_passthrough(self):
        """Test that GovernedAgent passes through attributes to wrapped agent."""
        mock_agent = MagicMock
        mock_agent.role = "Senior Analyst"
        mock_agent.custom_method.return_value = "test_result"

        gov_agent = GovernedAgent(agent=mock_agent, agent_code="TEST-001")

        # Access attributes that don't exist on GovernedAgent
        assert gov_agent.role == "Senior Analyst"
        assert gov_agent.custom_method == "test_result"


class TestGovernedCrew:
    """Test the GovernedCrew wrapper."""

    def test_governed_crew_initialization(self):
        """Test GovernedCrew initialization."""
        mock_crew = MagicMock
        agent_codes = {"analyst": "FI-001", "manager": "MGR-001"}

        gov_crew = GovernedCrew(
            crew=mock_crew,
            agent_codes=agent_codes,
            calling_system="SAP_S4HANA",
        )

        assert gov_crew.agent_codes == agent_codes
        assert gov_crew.calling_system == "SAP_S4HANA"
        assert gov_crew._crew is mock_crew

    def test_kickoff_all_agents_approved(self):
        """Test crew kickoff when all agents are APPROVED."""
        mock_crew = MagicMock
        mock_crew.kickoff.return_value = {"status": "completed"}

        agent_codes = {"analyst": "FI-001", "manager": "MGR-001"}
        gov_crew = GovernedCrew(crew=mock_crew, agent_codes=agent_codes)

        # Mock governance to approve all agents
        with patch.object(gov_crew._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            result = gov_crew.kickoff(inputs={"task_type": "analysis"})

            # Verify governance was called for each agent
            assert mock_evaluate.call_count == 2

            # Verify crew.kickoff was called
            mock_crew.kickoff.assert_called_once
            assert result == {"status": "completed"}

    def test_kickoff_agent_blocked(self):
        """Test crew kickoff when one agent is BLOCKED."""
        mock_crew = MagicMock
        agent_codes = {"analyst": "FI-001", "manager": "MGR-001"}
        gov_crew = GovernedCrew(crew=mock_crew, agent_codes=agent_codes)

        # Mock governance to block the second agent
        call_count = 0

        def mock_evaluate_side_effect(envelope):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return GovernanceVerdict(verdict="APPROVED", approved=True)
            else:
                return GovernanceVerdict(
                    verdict="BLOCKED",
                    approved=False,
                    reason="Agent not authorized",
                )

        with patch.object(gov_crew._gov, "evaluate") as mock_evaluate:
            mock_evaluate.side_effect = mock_evaluate_side_effect

            with pytest.raises(PermissionError) as exc_info:
                gov_crew.kickoff

            assert "Crew blocked" in str(exc_info.value)
            assert "not authorized" in str(exc_info.value)

            # Verify crew.kickoff was NOT called
            mock_crew.kickoff.assert_not_called

    def test_kickoff_without_inputs(self):
        """Test crew kickoff without inputs."""
        mock_crew = MagicMock
        mock_crew.kickoff.return_value = {"status": "completed"}

        agent_codes = {"analyst": "FI-001"}
        gov_crew = GovernedCrew(crew=mock_crew, agent_codes=agent_codes)

        with patch.object(gov_crew._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            result = gov_crew.kickoff

            # Verify crew.kickoff was called without inputs
            mock_crew.kickoff.assert_called_once_with

    def test_kickoff_with_inputs(self):
        """Test crew kickoff with inputs."""
        mock_crew = MagicMock
        mock_crew.kickoff.return_value = {"status": "completed"}

        agent_codes = {"analyst": "FI-001"}
        gov_crew = GovernedCrew(crew=mock_crew, agent_codes=agent_codes)

        with patch.object(gov_crew._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict(
                verdict="APPROVED",
                approved=True,
            )

            inputs = {"task": "analyze", "data_source": "ledger"}
            result = gov_crew.kickoff(inputs=inputs)

            # Verify crew.kickoff was called with inputs
            mock_crew.kickoff.assert_called_once_with(inputs=inputs)

            # Verify inputs were sent in governance context
            envelope = mock_evaluate.call_args[0][0]
            assert envelope.context["inputs"] == inputs

    def test_attribute_passthrough(self):
        """Test that GovernedCrew passes through attributes to wrapped crew."""
        mock_crew = MagicMock
        mock_crew.name = "Analysis Crew"
        mock_crew.custom_prop = "test_value"

        agent_codes = {"analyst": "FI-001"}
        gov_crew = GovernedCrew(crew=mock_crew, agent_codes=agent_codes)

        assert gov_crew.name == "Analysis Crew"
        assert gov_crew.custom_prop == "test_value"


class TestGovernCrewFactory:
    """Test the govern_crew convenience factory."""

    def test_govern_crew_factory(self):
        """Test govern_crew factory creates GovernedCrew."""
        mock_crew = MagicMock
        agent_codes = {"analyst": "FI-001", "manager": "MGR-001"}

        gov_crew = govern_crew(
            crew=mock_crew,
            agent_codes=agent_codes,
            calling_system="SAP_S4HANA",
        )

        assert isinstance(gov_crew, GovernedCrew)
        assert gov_crew.agent_codes == agent_codes
        assert gov_crew.calling_system == "SAP_S4HANA"


class TestFailOpenFailSafe:
    """Test fail-open and fail-safe behaviors."""

    def test_governed_agent_fail_open_on_server_error(self):
        """Test GovernedAgent allows execution when server is unreachable (fail-open)."""
        mock_agent = MagicMock
        mock_agent.execute_task.return_value = {"result": "success"}

        mock_task = MagicMock
        mock_task.description = "Analyze data"

        gov_agent = GovernedAgent(
            agent=mock_agent,
            agent_code="FI-001",
            fail_open=True,
        )

        # Mock server error
        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict.approved_offline

            result = gov_agent.execute_task(mock_task)

            # Task should execute despite server error
            assert result == {"result": "success"}
            mock_agent.execute_task.assert_called_once

    def test_governed_agent_fail_safe_on_server_error(self):
        """Test GovernedAgent blocks execution when server is unreachable (fail-safe)."""
        mock_agent = MagicMock
        mock_task = MagicMock
        mock_task.description = "Analyze data"

        gov_agent = GovernedAgent(
            agent=mock_agent,
            agent_code="FI-001",
            fail_open=False,
        )

        # Mock server error with fail-safe
        with patch.object(gov_agent._gov, "evaluate") as mock_evaluate:
            mock_evaluate.return_value = GovernanceVerdict.blocked_offline

            with pytest.raises(PermissionError):
                gov_agent.execute_task(mock_task)

            # Task should NOT execute
            mock_agent.execute_task.assert_not_called
