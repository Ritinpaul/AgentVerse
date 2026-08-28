"""
agentgovern-openai — Governance connector for OpenAI Agents SDK.

Wraps the OpenAI Agents SDK `Runner` and individual `Agent` objects
to intercept every run and pre-authorize through AgentGovern OS.

Install::
    pip install agentgovern-openai

Usage::
    from agents import Agent, Runner
    from agentgovern_openai import govern_agent, GovernedRunner

    # Wrap a single Agent
    agent = Agent(name="Triage Agent", instructions="...", tools=[...])
    governed = govern_agent(agent, agent_code="SUPPORT-001")

    # Or wrap the Runner for full run-level governance
    runner = GovernedRunner(agent_code="SUPPORT-001")
    result = await runner.run(governed, "Refund $200 to customer #4821")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from connectors.sdk.govcore import GovCore, GovernanceEnvelope, GovernanceVerdict

logger = logging.getLogger("agentgovern.openai")
AGENT_SOURCE = "openai_agents_sdk"


class GovernedRunner:
    """
    A governance wrapper around the OpenAI Agents SDK Runner.
    Pre-authorizes every agent run before delegating to the real runner.

    Example::
        import asyncio
        from agents import Agent
        from agentgovern_openai import GovernedRunner

        agent = Agent(name="Support Agent", instructions="Help customers.")
        gov_runner = GovernedRunner(agent_code="SUPPORT-001", calling_system="Zendesk")
        result = asyncio.run(gov_runner.run(agent, "Process refund for order #123"))
    """

    def __init__(
        self,
        agent_code: str,
        calling_system: str = "",
        server: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self.agent_code = agent_code
        self.calling_system = calling_system
        self._gov = GovCore(server=server, fail_open=fail_open)

    async def run(self, agent: Any, input: str, **kwargs) -> Any:
        """Authorize then run the OpenAI agent."""
        # Import here so the connector doesn't hard-fail if sdk isn't installed
        try:
            from agents import Runner
        except ImportError:
            raise ImportError(
                "The 'openai-agents' package is not installed. "
                "Run: pip install openai-agents"
            )

        verdict = self._gov.evaluate(GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=f"agents_sdk_run:{input[:100]}",
            agent_source=AGENT_SOURCE,
            context={"input": input, "agent_name": getattr(agent, "name", "unknown")},
            calling_system=self.calling_system,
        ))

        if not verdict.approved:
            logger.warning(
                "[OpenAI Connector] BLOCKED %s → %s | %s",
                self.agent_code, input[:60], verdict.reason,
            )
            raise PermissionError(
                f"[AgentGovern] Action blocked for {self.agent_code}: {verdict.reason}"
            )

        logger.info("[OpenAI Connector] APPROVED %s → running...", self.agent_code)
        return await Runner.run(agent, input, **kwargs)

    def run_sync(self, agent: Any, input: str, **kwargs) -> Any:
        """Synchronous version using Runner.run_sync."""
        try:
            from agents import Runner
        except ImportError:
            raise ImportError("The 'openai-agents' package is not installed.")

        verdict = self._gov.evaluate(GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=f"agents_sdk_run_sync:{input[:100]}",
            agent_source=AGENT_SOURCE,
            context={"input": input, "agent_name": getattr(agent, "name", "unknown")},
            calling_system=self.calling_system,
        ))

        if not verdict.approved:
            raise PermissionError(
                f"[AgentGovern] Action blocked for {self.agent_code}: {verdict.reason}"
            )
        return Runner.run_sync(agent, input, **kwargs)


def govern_agent(agent: Any, agent_code: str, **kwargs) -> "GovernedAgentWrapper":
    """Convenience factory: wrap a single OpenAI Agent with governance."""
    return GovernedAgentWrapper(agent, agent_code=agent_code, **kwargs)


class GovernedAgentWrapper:
    """Thin wrapper that attaches governance metadata to an OpenAI Agent."""

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
        self._runner = GovernedRunner(
            agent_code=agent_code,
            calling_system=calling_system,
            server=server,
            fail_open=fail_open,
        )

    async def run(self, input: str, **kwargs) -> Any:
        return await self._runner.run(self._agent, input, **kwargs)

    def run_sync(self, input: str, **kwargs) -> Any:
        return self._runner.run_sync(self._agent, input, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)
