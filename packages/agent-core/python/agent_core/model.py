"""
packages/agent-core/python/agent_core/model.py

Python mirror of the canonical Agent domain model.
Maintains exact parity with TypeScript packages/agent-core/src/model/agent.ts.
"""

import json
import hashlib
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, RootModel


class SandboxProfile(str, Enum):
    NONE = "none"
    DOCKER = "docker"
    GVISOR = "gvisor"
    FIRECRACKER = "firecracker"


class TraceLevel(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    DEBUG = "debug"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecretRef(BaseModel):
    secret_ref: str = Field(..., alias="secretRef")


class ModelFallback(BaseModel):
    provider: str
    name: str


class ModelRouting(BaseModel):
    max_cost_per_run: Optional[float] = Field(None, alias="maxCostPerRun")
    max_latency_ms: Optional[int] = Field(None, alias="maxLatencyMs")
    data_residency: Optional[str] = Field(None, alias="dataResidency")


class ModelConfig(BaseModel):
    provider: Literal["openai", "anthropic", "google", "ollama", "openrouter"]
    name: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = Field(None, alias="maxTokens")
    fallbacks: Optional[List[ModelFallback]] = None
    routing: Optional[ModelRouting] = None


class ToolPermissions(BaseModel):
    egress: Optional[List[str]] = None


class ToolReference(BaseModel):
    id: str
    type: Literal["mcp", "http", "native"]
    server: Optional[str] = None
    tool: Optional[str] = None
    url: Optional[str] = None
    version: Optional[str] = None
    risk: Optional[RiskLevel] = RiskLevel.LOW
    permissions: Optional[ToolPermissions] = None


class WorkflowNode(BaseModel):
    id: str
    type: Literal[
        "llm", "tool", "condition", "parallel", "loop",
        "retry", "human_approval", "subagent", "input", "output"
    ]
    label: Optional[str] = None
    tool_ref: Optional[str] = Field(None, alias="toolRef")
    config: Optional[Dict[str, Any]] = None


class WorkflowEdge(BaseModel):
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    condition: Optional[str] = None


class WorkflowGraph(BaseModel):
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []


class ApprovalConfig(BaseModel):
    high_risk_tool_calls: Literal["required", "log", "auto"] = Field(
        "required", alias="highRiskToolCalls"
    )
    critical_risk_tool_calls: Literal["block", "required"] = Field(
        "block", alias="criticalRiskToolCalls"
    )


class PolicyConfig(BaseModel):
    policy_bundle: Optional[str] = Field(None, alias="policyBundle")
    approval: Optional[ApprovalConfig] = Field(default_factory=ApprovalConfig)


class BudgetConfig(BaseModel):
    max_cost_per_run: Optional[float] = Field(None, alias="maxCostPerRun")
    max_tokens_per_run: Optional[int] = Field(None, alias="maxTokensPerRun")
    max_runs_per_day: Optional[int] = Field(None, alias="maxRunsPerDay")
    daily_limit: Optional[float] = Field(None, alias="dailyLimit")


class RuntimeConfig(BaseModel):
    sandbox: SandboxProfile = SandboxProfile.DOCKER
    egress: Literal["open", "restricted", "none"] = "restricted"
    timeout_seconds: Optional[int] = Field(120, alias="timeoutSeconds")
    max_tool_calls: Optional[int] = Field(20, alias="maxToolCalls")
    max_depth: Optional[int] = Field(4, alias="maxDepth")
    max_output_bytes: Optional[int] = Field(None, alias="maxOutputBytes")
    max_concurrent_runs: Optional[int] = Field(None, alias="maxConcurrentRuns")


class MemoryConfig(BaseModel):
    type: Literal["ephemeral", "persistent", "semantic"] = "ephemeral"
    max_tokens: Optional[int] = Field(None, alias="maxTokens")


class ObservabilityConfig(BaseModel):
    trace_level: TraceLevel = Field(TraceLevel.STANDARD, alias="traceLevel")
    redact_prompts: Optional[bool] = Field(True, alias="redactPrompts")


class Trigger(BaseModel):
    type: Literal["webhook", "schedule"]
    cron: Optional[str] = None


class SandboxTest(BaseModel):
    name: str
    input: str
    expected_behavior: str = Field(..., alias="expectedBehavior")


class AgentMetadata(BaseModel):
    api_version: Literal["agentstudio/v1"] = Field("agentstudio/v1", alias="apiVersion")
    kind: Literal["Agent"] = "Agent"
    name: str = Field(..., pattern=r"^[a-z0-9-]+$")
    version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    description: Optional[str] = None
    framework: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


class AgentManifest(BaseModel):
    metadata: AgentMetadata
    model: ModelConfig
    instructions: str
    tools: List[ToolReference] = []
    workflow: Optional[WorkflowGraph] = None
    policies: PolicyConfig = Field(default_factory=PolicyConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    memory: Optional[MemoryConfig] = None
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    env: Optional[Dict[str, Union[str, SecretRef]]] = None
    triggers: Optional[List[Trigger]] = None
    sandbox_tests: Optional[List[SandboxTest]] = Field(None, alias="sandboxTests")

    @property
    def canonical_hash(self) -> str:
        """
        Computes deterministic sha256 canonical hash of the manifest.
        """
        data = self.model_dump(mode="json", by_alias=True, exclude_none=True)
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
