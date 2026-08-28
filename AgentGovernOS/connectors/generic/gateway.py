"""
agentgovern-generic — Universal webhook connector for ANY system.

This is the framework-agnostic connector. Use it when:
  - Your AI agent is built with a custom/internal framework
  - You want to govern ANY HTTP-based system via webhooks
  - You need a simple Python function wrapper

Install::
    pip install agentgovern-generic

Usage::

    # Option A: Simple function decorator
    from agentgovern_generic import governed_action

    @governed_action(agent_code="MY-AGENT-001", action="process_payment")
    def process_payment(amount: float, account: str) -> dict:
        # Your business logic here — only runs if APPROVED
        return {"status": "success", "amount": amount}

    result = process_payment(amount=5000.0, account="ACC-123")

    # Option B: Manual evaluation
    from agentgovern_generic import GovernanceGateway

    gw = GovernanceGateway(agent_code="MY-AGENT-001")
    verdict = gw.check("send_email", context={"to": "ceo@company.com", "subject": "..."})
    if verdict.approved:
        send_the_email(...)

    # Option C: HTTP Webhook middleware
    # POST /webhook → evaluate → forward to your system
    from agentgovern_generic import WebhookMiddleware
    middleware = WebhookMiddleware(agent_code="MY-AGENT-001")
    result = middleware.handle(event_dict)
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from connectors.sdk.govcore import GovCore, GovernanceEnvelope, GovernanceVerdict

logger = logging.getLogger("agentgovern.generic")
AGENT_SOURCE = "generic"


class GovernanceGateway:
    """
    The universal governance gateway for any agent or system.

    Example::
        from agentgovern_generic import GovernanceGateway

        gw = GovernanceGateway(agent_code="CUSTOM-BOT-001", calling_system="MyApp")
        verdict = gw.check("delete_user", context={"user_id": 42, "reason": "GDPR"})
        if not verdict.approved:
            raise PermissionError(verdict.reason)
    """

    def __init__(
        self,
        agent_code: str,
        calling_system: str = "",
        server: Optional[str] = None,
        api_key: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self.agent_code = agent_code
        self.calling_system = calling_system
        self._gov = GovCore(server=server, api_key=api_key, fail_open=fail_open)

    def check(self, action: str, context: Optional[Dict] = None) -> GovernanceVerdict:
        """
        Check if an action is permitted.

        Args:
            action:  Short description of the action (e.g. "delete_record", "send_wire")
            context: Arbitrary dictionary of context (amount, target, justification, etc.)

        Returns:
            GovernanceVerdict with .approved (bool) and .reason (str)
        """
        envelope = GovernanceEnvelope(
            agent_code=self.agent_code,
            action_requested=action,
            agent_source=AGENT_SOURCE,
            context=context or {},
            calling_system=self.calling_system,
        )
        verdict = self._gov.evaluate(envelope)
        if verdict.approved:
            logger.info("[Generic Connector] APPROVED %s → %s", self.agent_code, action)
        else:
            logger.warning(
                "[Generic Connector] %s %s → %s | %s",
                verdict.verdict, self.agent_code, action, verdict.reason,
            )
        return verdict

    def require(self, action: str, context: Optional[Dict] = None) -> GovernanceVerdict:
        """
        Like check but raises PermissionError if not approved.
        Use for strict enforcement where you want exceptions on denial.
        """
        verdict = self.check(action, context)
        if not verdict.approved:
            raise PermissionError(
                f"[AgentGovern] '{action}' blocked for {self.agent_code}: {verdict.reason}"
            )
        return verdict


class WebhookMiddleware:
    """
    Governance middleware for HTTP/webhook-based agent systems.

    Normalizes incoming event dicts into GovernanceEnvelopes, evaluates them,
    and returns a structured result.

    Example::
        from agentgovern_generic import WebhookMiddleware

        middleware = WebhookMiddleware(agent_code="SAP-AGENT-001")

        # In your webhook handler:
        @app.post("/agent/execute")
        async def execute(event: dict):
            result = middleware.handle(event)
            if not result["approved"]:
                return {"error": result["reason"]}, 403
            # Proceed with the actual action
    """

    def __init__(
        self,
        agent_code: str,
        calling_system: str = "",
        action_key: str = "action",
        context_key: str = "context",
        server: Optional[str] = None,
    ):
        self.agent_code = agent_code
        self.action_key = action_key
        self.context_key = context_key
        self._gw = GovernanceGateway(
            agent_code=agent_code,
            calling_system=calling_system,
            server=server,
        )

    def handle(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a webhook event dict.
        Returns a dict with 'approved', 'verdict', 'reason', 'audit_id'.
        """
        action = event.get(self.action_key, event.get("type", "unknown_action"))
        context = event.get(self.context_key, {k: v for k, v in event.items if k != self.action_key})

        verdict = self._gw.check(str(action), context)
        return {
            "approved": verdict.approved,
            "verdict": verdict.verdict,
            "risk_score": verdict.risk_score,
            "reason": verdict.reason,
            "audit_id": verdict.audit_id,
            "requires_human_review": verdict.requires_human_review,
            "mode": verdict.mode,
        }


def governed_action(
    agent_code: str,
    action: Optional[str] = None,
    calling_system: str = "",
    context_from_kwargs: Optional[list] = None,
    server: Optional[str] = None,
    fail_open: Optional[bool] = None,
) -> Callable:
    """
    Decorator to govern any Python function.

    The function only executes if the governance API approves the action.
    If denied, raises PermissionError.

    Args:
        agent_code:           The agent identifier.
        action:               Action name. Defaults to function name.
        calling_system:       System triggering the call.
        context_from_kwargs:  List of kwarg names to include in the governance context.

    Example::
        @governed_action(agent_code="FI-001", action="approve_payment",
                         context_from_kwargs=["amount", "currency"])
        def approve_payment(amount: float, currency: str, vendor: str):
            # Only runs if AgentGovern approves
            return process_payment(amount, currency, vendor)
    """
    def decorator(func: Callable) -> Callable:
        gw = GovernanceGateway(
            agent_code=agent_code,
            calling_system=calling_system,
            server=server,
            fail_open=fail_open,
        )
        resolved_action = action or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Build context from specified kwargs
            context = {k: kwargs[k] for k in (context_from_kwargs or []) if k in kwargs}
            # Also include positional args as arg0, arg1...
            for i, a in enumerate(args):
                context[f"arg{i}"] = str(a)[:100]

            gw.require(resolved_action, context)
            return func(*args, **kwargs)

        return wrapper
    return decorator
