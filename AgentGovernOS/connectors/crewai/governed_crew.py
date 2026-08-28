"""
agentgovern-crewai — Governance connector for CrewAI agents.

Install::
    pip install agentgovern-crewai

Usage::
    from agentgovern_crewai import govern_crew, GovernedAgent

    # Option A: Wrap a single agent
    from crewai import Agent
    agent = Agent(role="Analyst", ...)
    governed = GovernedAgent(agent, agent_code="FI-ANALYST-001")
    # governed.execute_task(task) automatically checks governance before running.

    # Option B: Wrap an entire Crew
    from crewai import Crew, Agent, Task
    crew = Crew(agents=[analyst, manager], tasks=[task1])
    governed_crew = govern_crew(crew, agent_codes={"analyst": "FI-ANALYST-001"})
    governed_crew.kickoff  # Each task is pre-authorized
"""

from __future__ import annotations

import logging
import os
from functools import wraps
from typing import Any, Callable, Dict, Optional

from connectors.sdk.govcore import GovCore, GovernanceEnvelope, GovernanceVerdict

logger = logging.getLogger("agentgovern.crewai")

AGENT_SOURCE = "crewai"


class GovernedAgent:
    """
    A thin governance wrapper around any CrewAI Agent.

    Every time this agent is asked to execute a task, the action is
    pre-authorized through the AgentGovern Governance API.

    Example::

        from crewai import Agent
        from agentgovern_crewai import GovernedAgent

        raw_agent = Agent(
            role="Senior Financial Analyst",
            goal="Analyze investment portfolios",
            backstory="Expert in financial analysis with 20 years experience",
            tools=[read_ledger_tool, calculate_tool],
        )

        governed_agent = GovernedAgent(
            agent=raw_agent,
            agent_code="FI-ANALYST-001",
            calling_system="SAP_S4HANA",
        )
    """

    def __init__(
        self,
        agent: Any,
        agent_code: str,
        calling_system: str = "",
        server: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self._agent = agent
        self.agent_code = agent_code
        self.calling_system = calling_system
        self._gov = GovCore(server=server, fail_open=fail_open)
        logger.info("[CrewAI Connector] GovernedAgent initialized: %s", agent_code)

    def _authorize(self, action: str, context: dict) -> GovernanceVerdict:
        envelope = GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=action,
            agent_source=AGENT_SOURCE,
            context=context,
            calling_system=self.calling_system,
        )
        verdict = self._gov.evaluate(envelope)
        if verdict.approved:
            logger.info("[CrewAI Connector] APPROVED: %s → %s", self.agent_code, action)
        else:
            logger.warning(
                "[CrewAI Connector] %s: %s → %s | reason: %s",
                verdict.verdict, self.agent_code, action, verdict.reason,
            )
        return verdict

    def execute_task(self, task: Any, context: dict = None) -> Any:
        """Execute a CrewAI task with governance pre-authorization."""
        action = f"execute_task:{getattr(task, 'description', str(task))[:80]}"
        verdict = self._authorize(action, context or {})
        if not verdict.approved:
            raise PermissionError(
                f"[AgentGovern] Action blocked for {self.agent_code}: {verdict.reason}"
            )
        # Delegate to the underlying CrewAI agent
        return self._agent.execute_task(task, context)

    def __getattr__(self, name: str) -> Any:
        """Pass through any other attribute access to the underlying agent."""
        return getattr(self._agent, name)


class GovernedCrew:
    """
    A governance wrapper around a CrewAI Crew.
    Intercepts kickoff and authorizes each agent's participation.

    Example::
        from crewai import Crew, Agent, Task
        from agentgovern_crewai import GovernedCrew

        crew = Crew(agents=[analyst, manager], tasks=[task1, task2])
        governed = GovernedCrew(crew, agent_codes={"analyst": "FI-001", "manager": "MGR-001"})
        result = governed.kickoff
    """

    def __init__(
        self,
        crew: Any,
        agent_codes: Dict[str, str],
        calling_system: str = "",
        server: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self._crew = crew
        self.agent_codes = agent_codes          # e.g. {"analyst": "FI-001"}
        self.calling_system = calling_system
        self._gov = GovCore(server=server, fail_open=fail_open)

    def kickoff(self, inputs: Optional[dict] = None) -> Any:
        """Authorize all agents, then delegate to the real crew.kickoff."""
        for role, code in self.agent_codes.items:
            verdict = self._gov.evaluate(GovernanceEnvelope(
                agent_code=code,
                action_requested="crew_kickoff",
                agent_source=AGENT_SOURCE,
                context={"role": role, "inputs": inputs or {}},
                calling_system=self.calling_system,
            ))
            if not verdict.approved:
                raise PermissionError(
                    f"[AgentGovern] Crew blocked — agent {code} ({role}) not authorized: "
                    f"{verdict.reason}"
                )
        return self._crew.kickoff(inputs=inputs) if inputs else self._crew.kickoff

    def __getattr__(self, name: str) -> Any:
        return getattr(self._crew, name)


def govern_crew(
    crew: Any,
    agent_codes: Dict[str, str],
    calling_system: str = "",
) -> GovernedCrew:
    """Convenience factory: wrap a Crew with governance in one line."""
    return GovernedCrew(crew, agent_codes=agent_codes, calling_system=calling_system)
