"""
agentgovern-langchain — Governance connector for LangChain agents.

Wraps LangChain's AgentExecutor and BaseTool to intercept every
tool call and pre-authorize it through AgentGovern OS.

Install::
    pip install agentgovern-langchain

Usage::
    from langchain.agents import AgentExecutor
    from agentgovern_langchain import GovernedAgentExecutor

    # Wrap your existing executor
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    governed = GovernedAgentExecutor(executor, agent_code="SUPPORT-001")
    result = governed.invoke({"input": "Refund $500 to customer #4821"})
    # → Calls governance API before invoking the agent
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterator, List, Optional, Union

from connectors.sdk.govcore import GovCore, GovernanceEnvelope, GovernanceVerdict

logger = logging.getLogger("agentgovern.langchain")
AGENT_SOURCE = "langchain"


class GovernedAgentExecutor:
    """
    A drop-in replacement for LangChain's AgentExecutor that pre-authorizes
    every invocation through the AgentGovern Governance API.

    Example::
        from langchain.agents import AgentExecutor
        from agentgovern_langchain import GovernedAgentExecutor

        raw_executor = AgentExecutor.from_agent_and_tools(agent, tools)
        governed = GovernedAgentExecutor(
            executor=raw_executor,
            agent_code="SUPPORT-BOT-001",
            calling_system="Zendesk",
        )
        result = governed.invoke({"input": "Issue refund of $150"})
    """

    def __init__(
        self,
        executor: Any,
        agent_code: str,
        calling_system: str = "",
        server: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self._executor = executor
        self.agent_code = agent_code
        self.calling_system = calling_system
        self._gov = GovCore(server=server, fail_open=fail_open)
        logger.info("[LangChain Connector] GovernedAgentExecutor initialized: %s", agent_code)

    def _authorize(self, input_text: str, context: dict = None) -> GovernanceVerdict:
        action = f"llm_invoke:{input_text[:100]}"
        envelope = GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=action,
            agent_source=AGENT_SOURCE,
            context={"input": input_text, **(context or {})},
            calling_system=self.calling_system,
        )
        verdict = self._gov.evaluate(envelope)
        if not verdict.approved:
            logger.warning(
                "[LangChain Connector] BLOCKED %s: %s | %s",
                self.agent_code, action, verdict.reason,
            )
        return verdict

    def invoke(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Authorize then invoke."""
        input_text = inputs.get("input", str(inputs)[:100])
        verdict = self._authorize(input_text, inputs)
        if not verdict.approved:
            return {
                "output": f"[BLOCKED by AgentGovern] {verdict.reason}",
                "governance_verdict": verdict.verdict,
                "governance_audit_id": verdict.audit_id,
            }
        result = self._executor.invoke(inputs, **kwargs)
        # Enrich output with governance context
        if isinstance(result, dict):
            result["governance_verdict"] = verdict.verdict
            result["governance_audit_id"] = verdict.audit_id
        return result

    def stream(self, inputs: Dict[str, Any], **kwargs) -> Iterator:
        """Authorize then stream."""
        input_text = inputs.get("input", str(inputs)[:100])
        verdict = self._authorize(input_text, inputs)
        if not verdict.approved:
            yield {"output": f"[BLOCKED by AgentGovern] {verdict.reason}"}
            return
        yield from self._executor.stream(inputs, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._executor, name)


class GovernedTool:
    """
    Wrap an individual LangChain BaseTool so that each tool call is
    pre-authorized through the governance API.

    Useful when you want fine-grained tool-level governance rather than
    top-level invocation governance.

    Example::
        from langchain.tools import StructuredTool
        from agentgovern_langchain import GovernedTool

        raw_tool = StructuredTool.from_function(my_function)
        governed_tool = GovernedTool(raw_tool, agent_code="FI-001")
        # Pass governed_tool into your AgentExecutor
    """

    def __init__(
        self,
        tool: Any,
        agent_code: str,
        calling_system: str = "",
        server: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self._tool = tool
        self.agent_code = agent_code
        self.calling_system = calling_system
        self._gov = GovCore(server=server, fail_open=fail_open)

    def run(self, tool_input: Union[str, dict], **kwargs) -> str:
        action = f"tool:{getattr(self._tool, 'name', 'unknown')}"
        envelope = GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=action,
            agent_source=AGENT_SOURCE,
            context={"tool_input": str(tool_input)[:200]},
            calling_system=self.calling_system,
        )
        verdict = self._gov.evaluate(envelope)
        if not verdict.approved:
            return f"[BLOCKED by AgentGovern] Tool '{action}' denied: {verdict.reason}"
        return self._tool.run(tool_input, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._tool, name)
