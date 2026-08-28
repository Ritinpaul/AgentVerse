"""
agentgovern-anthropic — Governance connector for Anthropic Claude agents.

Wraps the Anthropic Python SDK's `client.messages.create` to pre-authorize
every message call through AgentGovern OS before the LLM is invoked.

Install::
    pip install agentgovern-anthropic

Usage::
    import anthropic
    from agentgovern_anthropic import GovernedAnthropicClient

    client = anthropic.Anthropic
    governed = GovernedAnthropicClient(client, agent_code="LEGAL-REVIEW-001")

    # Exact same API as the real client — governance is transparent
    message = governed.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Summarize this contract..."}]
    )
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from connectors.sdk.govcore import GovCore, GovernanceEnvelope, GovernanceVerdict

logger = logging.getLogger("agentgovern.anthropic")
AGENT_SOURCE = "anthropic"


class _GovernedMessages:
    """
    Mimics `anthropic.resources.Messages` but intercepts `.create` calls.
    Access via governed_client.messages.create(...).
    """

    def __init__(self, messages_resource: Any, gov: GovCore, agent_code: str, calling_system: str):
        self._messages = messages_resource
        self._gov = gov
        self.agent_code = agent_code
        self.calling_system = calling_system

    def create(self, messages: List[dict], model: str = "", **kwargs) -> Any:
        # Extract the user's intent from the first user message
        user_content = next(
            (m.get("content", "") for m in messages if m.get("role") == "user"),
            "anthropic_message",
        )
        action = f"messages.create:{str(user_content)[:100]}"

        verdict = self._gov.evaluate(GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=action,
            agent_source=AGENT_SOURCE,
            context={
                "model": model,
                "message_count": len(messages),
                "first_user_message": str(user_content)[:200],
            },
            calling_system=self.calling_system,
        ))

        if not verdict.approved:
            logger.warning(
                "[Anthropic Connector] BLOCKED %s | %s", self.agent_code, verdict.reason,
            )
            raise PermissionError(
                f"[AgentGovern] Message blocked for {self.agent_code}: {verdict.reason}"
            )

        logger.info("[Anthropic Connector] APPROVED %s → calling model %s", self.agent_code, model)
        return self._messages.create(messages=messages, model=model, **kwargs)

    def stream(self, messages: List[dict], model: str = "", **kwargs):
        """Governance-aware streaming version."""
        user_content = next(
            (m.get("content", "") for m in messages if m.get("role") == "user"),
            "stream_message",
        )
        verdict = self._gov.evaluate(GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=f"messages.stream:{str(user_content)[:100]}",
            agent_source=AGENT_SOURCE,
            context={"model": model, "message_count": len(messages)},
            calling_system=self.calling_system,
        ))
        if not verdict.approved:
            raise PermissionError(
                f"[AgentGovern] Stream blocked for {self.agent_code}: {verdict.reason}"
            )
        return self._messages.stream(messages=messages, model=model, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)


class GovernedAnthropicClient:
    """
    A transparent governance wrapper around the `anthropic.Anthropic` client.

    The API is identical to the real client — just swap it in.

    Example::
        import anthropic
        from agentgovern_anthropic import GovernedAnthropicClient

        raw_client = anthropic.Anthropic(api_key="sk-ant-...")
        client = GovernedAnthropicClient(
            client=raw_client,
            agent_code="LEGAL-REVIEW-001",
            calling_system="ContractVault",
        )

        # Same API, now governed:
        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Review this NDA..."}]
        )
    """

    def __init__(
        self,
        client: Any,
        agent_code: str,
        calling_system: str = "",
        server: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self._client = client
        self.agent_code = agent_code
        self.calling_system = calling_system
        self._gov = GovCore(server=server, fail_open=fail_open)

        # Replace the messages resource with our governed proxy
        self.messages = _GovernedMessages(
            messages_resource=client.messages,
            gov=self._gov,
            agent_code=agent_code,
            calling_system=calling_system,
        )
        logger.info("[Anthropic Connector] GovernedAnthropicClient initialized: %s", agent_code)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
