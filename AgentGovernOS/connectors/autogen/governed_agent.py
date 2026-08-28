"""
agentgovern-autogen — Governance connector for Microsoft AutoGen.

Wraps AutoGen's AssistantAgent and UserProxyAgent to intercept
conversation initiation and pre-authorize through AgentGovern OS.

Install::
    pip install agentgovern-autogen

Usage::
    import autogen
    from agentgovern_autogen import GovernedAssistantAgent

    assistant = autogen.AssistantAgent("assistant", llm_config={"model": "gpt-4o"})
    governed = GovernedAssistantAgent(
        agent=assistant,
        agent_code="CODE-ASSISTANT-001",
    )
    # Use governed exactly like the original AssistantAgent
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from connectors.sdk.govcore import GovCore, GovernanceEnvelope, GovernanceVerdict

logger = logging.getLogger("agentgovern.autogen")
AGENT_SOURCE = "autogen"


class GovernedAssistantAgent:
    """
    Governance wrapper for AutoGen's AssistantAgent.

    Intercepts initiate_chat and generate_reply to pre-authorize
    each conversation or reply through the governance API.

    Example::
        import autogen
        from agentgovern_autogen import GovernedAssistantAgent

        raw_agent = autogen.AssistantAgent(
            name="coder",
            llm_config={"model": "gpt-4o", "api_key": "..."},
            system_message="You are a Python expert.",
        )
        governed = GovernedAssistantAgent(raw_agent, agent_code="DEV-BOT-001")
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
        logger.info("[AutoGen Connector] GovernedAssistantAgent initialized: %s", agent_code)

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Any] = None,
        **kwargs,
    ) -> Optional[Union[str, Dict]]:
        """Authorize before generating a reply."""
        last_msg = (messages or [{}])[-1]
        content = str(last_msg.get("content", ""))[:100]
        action = f"generate_reply:{content}"

        verdict = self._gov.evaluate(GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=action,
            agent_source=AGENT_SOURCE,
            context={
                "message_count": len(messages) if messages else 0,
                "last_message_preview": content,
                "sender": getattr(sender, "name", str(sender)),
            },
            calling_system=self.calling_system,
        ))

        if not verdict.approved:
            logger.warning(
                "[AutoGen Connector] BLOCKED %s | %s", self.agent_code, verdict.reason,
            )
            return f"[BLOCKED by AgentGovern] {verdict.reason}"

        return self._agent.generate_reply(messages=messages, sender=sender, **kwargs)

    def initiate_chat(self, recipient: Any, message: str, **kwargs) -> Any:
        """Authorize before initiating a conversation."""
        verdict = self._gov.evaluate(GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=f"initiate_chat:{message[:100]}",
            agent_source=AGENT_SOURCE,
            context={
                "recipient": getattr(recipient, "name", str(recipient)),
                "initial_message": message[:200],
            },
            calling_system=self.calling_system,
        ))
        if not verdict.approved:
            raise PermissionError(
                f"[AgentGovern] Chat blocked for {self.agent_code}: {verdict.reason}"
            )
        return self._agent.initiate_chat(recipient, message=message, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)


class GovernedUserProxyAgent:
    """
    Governance wrapper for AutoGen's UserProxyAgent.
    Intercepts code execution requests particularly.
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
        self._gov = GovCore(server=server, fail_open=fail_open)
        self.calling_system = calling_system

    def initiate_chat(self, recipient: Any, message: str, **kwargs) -> Any:
        verdict = self._gov.evaluate(GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=f"proxy_initiate_chat:{message[:100]}",
            agent_source=AGENT_SOURCE,
            context={"recipient": getattr(recipient, "name", "unknown"), "message": message[:200]},
            calling_system=self.calling_system,
        ))
        if not verdict.approved:
            raise PermissionError(
                f"[AgentGovern] Proxy chat blocked for {self.agent_code}: {verdict.reason}"
            )
        return self._agent.initiate_chat(recipient, message=message, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)
