"""
Tests: CrewAI Crew Integration (mock-based)

Validates the DisputeResolutionCrew and MetaCrew structure without
requiring a real crewai install or running Ollama. All crewai
classes are mocked.

For full end-to-end verification with real LLM: run inside Docker with
  docker compose exec crewai-engine python -c "
    from crews.dispute_crew import DisputeResolutionCrew
    import asyncio
    r = asyncio.run(DisputeResolutionCrew.resolve({
        'id': 'TEST-001',
        'description': 'Test dispute',
        'customer_id': 'ACM-001',
        'amount': 5000
    }))
    print(r)
  "
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call

CREWAI_ENGINE = os.path.join(os.path.dirname(__file__), "..", "services", "crewai-engine")
sys.path.insert(0, CREWAI_ENGINE)


# ──────────────────────────────────────────────────────────────
# Fixtures — mock crewai before importing dispute_crew
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_crewai_modules:
    """Inject mock crewai + agents into sys.modules so imports don't fail."""
    mock_agent = MagicMock(name="MockAgent")
    mock_task = MagicMock(name="MockTask")
    mock_crew_class = MagicMock(name="MockCrewClass")
    mock_process = MagicMock(name="MockProcess")
    mock_process.hierarchical = "hierarchical"

    # Mock crewai package
    mock_crewai = MagicMock
    mock_crewai.Agent = mock_agent
    mock_crewai.Task = mock_task
    mock_crewai.Crew = mock_crew_class
    mock_crewai.Process = mock_process

    # Mock core_crew agent factories
    mock_core_crew = MagicMock
    mock_core_crew.create_evidence_collector.return_value = MagicMock(name="evidence_collector")
    mock_core_crew.create_risk_evaluator.return_value = MagicMock(name="risk_evaluator")
    mock_core_crew.create_negotiation_strategist.return_value = MagicMock(name="negotiation_strategist")
    mock_core_crew.create_dispute_resolver.return_value = MagicMock(name="dispute_resolver")
    mock_core_crew.create_governance_sentinel.return_value = MagicMock(name="governance_sentinel")

    with patch.dict(sys.modules, {
        "crewai": mock_crewai,
        "agents": MagicMock,
        "agents.core_crew": mock_core_crew,
    }):
        yield {
            "crewai": mock_crewai,
            "Task": mock_task,
            "Crew": mock_crew_class,
            "Process": mock_process,
            "core_crew": mock_core_crew,
        }


@pytest.fixture
def sample_dispute:
    return {
        "id": "DISP-TEST-001",
        "description": "Customer claims short delivery on invoice INV-99123",
        "customer_id": "ACM-002",
        "amount": 42000.0,
        "dispute_type": "short_delivery",
    }


# ──────────────────────────────────────────────────────────────
# DisputeResolutionCrew Structure Tests
# ──────────────────────────────────────────────────────────────

class TestDisputeCrewStructure:

    def test_crew_instantiation_creates_five_agents(self, mock_crewai_modules):
        """DisputeResolutionCrew should create exactly 5 agents on init."""
        from importlib import import_module
        import importlib
        # Clear cached module if any
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew

        crew = DisputeResolutionCrew
        cc = mock_crewai_modules["core_crew"]
        cc.create_evidence_collector.assert_called_once
        cc.create_risk_evaluator.assert_called_once
        cc.create_negotiation_strategist.assert_called_once
        cc.create_dispute_resolver.assert_called_once
        cc.create_governance_sentinel.assert_called_once

    def test_build_crew_creates_four_tasks(self, mock_crewai_modules, sample_dispute):
        """_create_tasks should produce exactly 4 tasks."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew

        crew_instance = DisputeResolutionCrew
        tasks = crew_instance._create_tasks(sample_dispute)
        assert len(tasks) == 4

    def test_tasks_use_correct_agents(self, mock_crewai_modules, sample_dispute):
        """Each task should reference the right agent."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew
        Task = mock_crewai_modules["Task"]

        crew_instance = DisputeResolutionCrew
        crew_instance._create_tasks(sample_dispute)

        calls = Task.call_args_list
        assert len(calls) == 4

        # Task 1 → evidence_collector
        assert calls[0].kwargs["agent"] is crew_instance.evidence_collector
        # Task 2 → risk_evaluator
        assert calls[1].kwargs["agent"] is crew_instance.risk_evaluator
        # Task 3 → negotiation_strategist
        assert calls[2].kwargs["agent"] is crew_instance.negotiation_strategist
        # Task 4 → dispute_resolver
        assert calls[3].kwargs["agent"] is crew_instance.dispute_resolver

    def test_task_context_chain(self, mock_crewai_modules, sample_dispute):
        """Tasks 2-4 should have context from earlier tasks."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew
        Task = mock_crewai_modules["Task"]

        crew_instance = DisputeResolutionCrew
        crew_instance._create_tasks(sample_dispute)

        calls = Task.call_args_list
        # t1 has no context
        assert "context" not in calls[0].kwargs
        # t2 has context=[t1]
        assert "context" in calls[1].kwargs
        assert len(calls[1].kwargs["context"]) == 1
        # t3 has context=[t1, t2]
        assert len(calls[2].kwargs["context"]) == 2
        # t4 has context=[t1, t2, t3]
        assert len(calls[3].kwargs["context"]) == 3

    def test_build_crew_passes_manager_agent(self, mock_crewai_modules, sample_dispute):
        """build_crew should set governance_sentinel as manager_agent."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew
        Crew = mock_crewai_modules["Crew"]

        crew_instance = DisputeResolutionCrew
        crew_instance.build_crew(sample_dispute)

        crew_call = Crew.call_args
        assert crew_call.kwargs["manager_agent"] is crew_instance.governance_sentinel
        assert crew_call.kwargs["process"] == "hierarchical"
        assert crew_call.kwargs["memory"] is True

    def test_build_crew_includes_all_agents(self, mock_crewai_modules, sample_dispute):
        """build_crew Crew call should list all 5 agents."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew
        Crew = mock_crewai_modules["Crew"]

        crew_instance = DisputeResolutionCrew
        crew_instance.build_crew(sample_dispute)

        agents_arg = Crew.call_args.kwargs["agents"]
        assert len(agents_arg) == 5
        assert crew_instance.evidence_collector in agents_arg
        assert crew_instance.governance_sentinel in agents_arg

    def test_task_descriptions_contain_dispute_fields(self, mock_crewai_modules, sample_dispute):
        """Task descriptions should embed the dispute details."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew
        Task = mock_crewai_modules["Task"]

        crew_instance = DisputeResolutionCrew
        crew_instance._create_tasks(sample_dispute)

        # First task description should reference customer_id and amount
        t1_desc = Task.call_args_list[0].kwargs["description"]
        assert "ACM-002" in t1_desc
        assert "42" in t1_desc  # part of 42000

    def test_dispute_with_missing_fields_uses_defaults(self, mock_crewai_modules):
        """_create_tasks should not crash with a minimal dispute dict."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew

        crew_instance = DisputeResolutionCrew
        tasks = crew_instance._create_tasks({})  # empty dispute
        assert len(tasks) == 4


# ──────────────────────────────────────────────────────────────
# DisputeResolutionCrew.resolve Tests
# ──────────────────────────────────────────────────────────────

class TestDisputeCrewResolve:

    @pytest.mark.asyncio
    async def test_resolve_calls_kickoff_with_inputs(self, mock_crewai_modules, sample_dispute):
        """resolve should call crew.kickoff(inputs=dispute)."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew

        mock_result = MagicMock
        mock_result.tasks_output = [MagicMock]
        mock_result.tasks_output[0].__str__ = lambda self: "task output"
        mock_result.token_usage = {"prompt": 100, "completion": 50}

        Crew = mock_crewai_modules["Crew"]
        mock_crew_instance = Crew.return_value
        mock_crew_instance.kickoff.return_value = mock_result

        crew = DisputeResolutionCrew
        result = await crew.resolve(sample_dispute)

        mock_crew_instance.kickoff.assert_called_once_with(inputs=sample_dispute)

    @pytest.mark.asyncio
    async def test_resolve_returns_dict_with_expected_keys(self, mock_crewai_modules, sample_dispute):
        """resolve should return dict with 'raw', 'tasks_output', 'token_usage'."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew

        mock_result = MagicMock
        mock_result.tasks_output = []
        mock_result.token_usage = {"prompt": 200}

        Crew = mock_crewai_modules["Crew"]
        Crew.return_value.kickoff.return_value = mock_result

        crew = DisputeResolutionCrew
        result = await crew.resolve(sample_dispute)

        assert "raw" in result
        assert "tasks_output" in result
        assert "token_usage" in result
        assert isinstance(result["tasks_output"], list)
        assert result["token_usage"] == {"prompt": 200}

    @pytest.mark.asyncio
    async def test_resolve_handles_result_without_tasks_output(self, mock_crewai_modules, sample_dispute):
        """resolve should handle CrewOutput without tasks_output attr."""
        sys.modules.pop("crews.dispute_crew", None)
        sys.modules.pop("crews", None)

        from crews.dispute_crew import DisputeResolutionCrew

        mock_result = MagicMock(spec=[])  # no attributes
        mock_result.__str__ = lambda self: "crew raw result"

        Crew = mock_crewai_modules["Crew"]
        Crew.return_value.kickoff.return_value = mock_result

        crew = DisputeResolutionCrew
        result = await crew.resolve(sample_dispute)

        assert result["tasks_output"] == []
        assert result["token_usage"] == {}
