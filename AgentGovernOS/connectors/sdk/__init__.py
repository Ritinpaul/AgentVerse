"""agentgovern-sdk — base package init."""
from connectors.sdk.govcore import (
    GovCore,
    GovernanceEnvelope,
    GovernanceVerdict,
    evaluate,
    get_default_core,
    SDK_VERSION,
)

__version__ = SDK_VERSION
__all__ = [
    "GovCore",
    "GovernanceEnvelope",
    "GovernanceVerdict",
    "evaluate",
    "get_default_core",
]
