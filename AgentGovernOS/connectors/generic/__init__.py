"""agentgovern-generic connector."""
from connectors.generic.gateway import GovernanceGateway, WebhookMiddleware, governed_action
__all__ = ["GovernanceGateway", "WebhookMiddleware", "governed_action"]
