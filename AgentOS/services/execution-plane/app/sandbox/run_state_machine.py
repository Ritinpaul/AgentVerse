"""
app/sandbox/run_state_machine.py

Execution Plane Run State Machine & Step Telemetry Engine.
Manages run lifecycle: QUEUED -> VALIDATING -> POLICY_CHECK -> SCHEDULING ->
SANDBOX_PROVISIONING -> RUNNING -> COMPLETED / FAILED / BLOCKED / CANCELLED.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from app.sandbox.policy_interceptor import (
    RuntimePolicyInterceptor,
    ToolPolicyViolationError,
    EgressViolationError,
    BudgetExceededError
)

logger = logging.getLogger(__name__)


class RunState(str):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    POLICY_CHECK = "POLICY_CHECK"
    SCHEDULING = "SCHEDULING"
    SANDBOX_PROVISIONING = "SANDBOX_PROVISIONING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"


class RunStepRecord:
    def __init__(
        self,
        step_index: int,
        action: str,
        thought: Optional[str] = None,
        tool: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        output: Optional[str] = None,
        latency_ms: int = 0,
        cost_usd: float = 0.0
    ):
        self.step_index = step_index
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.action = action  # "THOUGHT", "TOOL_CALL", "OUTPUT", "BLOCKED", "ERROR"
        self.thought = thought
        self.tool = tool
        self.inputs = inputs or {}
        self.output = output
        self.latency_ms = latency_ms
        self.cost_usd = cost_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_index,
            "timestamp": self.timestamp,
            "action": self.action,
            "thought": self.thought,
            "tool": self.tool,
            "inputs": self.inputs,
            "output": self.output,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd
        }


class ExecutionRunInstance:
    def __init__(self, run_id: str, agent_id: str, manifest: Dict[str, Any]):
        self.run_id = run_id
        self.agent_id = agent_id
        self.manifest = manifest
        self.status = RunState.QUEUED
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.cumulative_cost_usd: float = 0.0
        self.policy_verdict: str = "ALLOW"
        self.denial_reason: Optional[str] = None
        self.steps: List[RunStepRecord] = []
        self.state_history: List[Dict[str, str]] = []
        self._record_state_change(RunState.QUEUED)

    def _record_state_change(self, new_state: str, note: Optional[str] = None):
        self.status = new_state
        self.state_history.append({
            "status": new_state,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": note or ""
        })

    def add_step(
        self,
        action: str,
        thought: Optional[str] = None,
        tool: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        output: Optional[str] = None,
        latency_ms: int = 0,
        cost_usd: float = 0.0
    ) -> RunStepRecord:
        step_idx = len(self.steps) + 1
        record = RunStepRecord(
            step_index=step_idx,
            action=action,
            thought=thought,
            tool=tool,
            inputs=inputs,
            output=output,
            latency_ms=latency_ms,
            cost_usd=cost_usd
        )
        self.steps.append(record)
        self.cumulative_cost_usd += cost_usd
        return record

    def run_execution(self, simulate_tool_calls: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Executes full state machine transition sequence.
        """
        self.started_at = datetime.utcnow().isoformat() + "Z"

        # State 1: VALIDATING
        self._record_state_change(RunState.VALIDATING, "Validating manifest parameters")
        if not self.manifest.get("model") or not self.manifest.get("instructions"):
            self._record_state_change(RunState.FAILED, "Manifest missing required model or instructions")
            return self.status

        # State 2: POLICY_CHECK
        self._record_state_change(RunState.POLICY_CHECK, "Pre-execution SENTINEL policy check")
        policy_cfg = self.manifest.get("policies") or {}
        budget_cfg = self.manifest.get("budget") or {}
        runtime_cfg = self.manifest.get("runtime") or {}

        max_cost = budget_cfg.get("maxCostPerRun") or budget_cfg.get("max_cost_per_run") or 10.0
        if max_cost > 10.0:
            self.policy_verdict = "DENY"
            self.denial_reason = f"Cost budget ${max_cost} exceeds $10.00 ceiling"
            self._record_state_change(RunState.BLOCKED, self.denial_reason)
            return self.status

        # State 3: SCHEDULING
        self._record_state_change(RunState.SCHEDULING, "Assigning execution worker node")

        # State 4: SANDBOX_PROVISIONING
        sandbox_type = runtime_cfg.get("sandbox", "docker")
        self._record_state_change(RunState.SANDBOX_PROVISIONING, f"Provisioning {sandbox_type} isolation container")

        # State 5: RUNNING
        self._record_state_change(RunState.RUNNING, "Executing agent prompt & tool workflow")

        # Step 1: Initial Reasoning Thought
        self.add_step(
            action="THOUGHT",
            thought=f"Received prompt directive: '{self.manifest.get('instructions')[:60]}...'. Preparing plan.",
            latency_ms=120,
            cost_usd=0.001
        )

        # Execute Tool Calls
        tool_calls_to_run = simulate_tool_calls or self.manifest.get("tools") or []
        for tool_data in tool_calls_to_run:
            tool_id = tool_data.get("id") or "unnamed-tool"
            tool_inputs = tool_data.get("inputs") or {}
            step_cost = tool_data.get("estimated_cost", 0.01)

            # Runtime Policy Interceptor Enforcement
            try:
                RuntimePolicyInterceptor.validate_tool_call(
                    tool=tool_data,
                    inputs=tool_inputs,
                    policy_cfg=policy_cfg,
                    runtime_cfg=runtime_cfg,
                    budget_cfg=budget_cfg,
                    current_cumulative_cost=self.cumulative_cost_usd,
                    step_estimated_cost=step_cost
                )
            except (ToolPolicyViolationError, EgressViolationError) as violation:
                self.denial_reason = str(violation)
                self.add_step(
                    action="BLOCKED",
                    thought=f"Tool '{tool_id}' execution intercepted by runtime policy gate.",
                    tool=tool_id,
                    inputs=tool_inputs,
                    output=f"BLOCKED: {str(violation)}",
                    latency_ms=10,
                    cost_usd=0.0
                )
                self._record_state_change(RunState.BLOCKED, str(violation))
                self.completed_at = datetime.utcnow().isoformat() + "Z"
                return self.status
            except BudgetExceededError as budget_err:
                self.denial_reason = str(budget_err)
                self.add_step(
                    action="ERROR",
                    thought="Execution terminated due to cost limit exceedance.",
                    tool=tool_id,
                    output=f"BUDGET_EXCEEDED: {str(budget_err)}",
                    latency_ms=5,
                    cost_usd=0.0
                )
                self._record_state_change(RunState.FAILED, str(budget_err))
                self.completed_at = datetime.utcnow().isoformat() + "Z"
                return self.status

            # Successful Tool Execution
            self.add_step(
                action="TOOL_CALL",
                thought=f"Invoking tool '{tool_id}'",
                tool=tool_id,
                inputs=tool_inputs,
                output=f"Successfully executed {tool_id}",
                latency_ms=180,
                cost_usd=step_cost
            )

        # Final Output Step
        self.add_step(
            action="OUTPUT",
            output=f"Agent completed workload successfully. Total steps: {len(self.steps)}.",
            latency_ms=80,
            cost_usd=0.002
        )

        self._record_state_change(RunState.COMPLETED, "Agent execution finished cleanly")
        self.completed_at = datetime.utcnow().isoformat() + "Z"
        return self.status


class RunExecutionManager:
    """
    In-memory registry of active and historical runs.
    """
    def __init__(self):
        self.runs: Dict[str, ExecutionRunInstance] = {}

    def create_run(self, agent_id: str, manifest: Dict[str, Any], run_id: Optional[str] = None) -> ExecutionRunInstance:
        rid = run_id or f"run-{uuid.uuid4().hex[:12]}"
        instance = ExecutionRunInstance(rid, agent_id, manifest)
        self.runs[rid] = instance
        return instance

    def get_run(self, run_id: str) -> Optional[ExecutionRunInstance]:
        return self.runs.get(run_id)

    def cancel_run(self, run_id: str) -> bool:
        instance = self.runs.get(run_id)
        if instance and instance.status in [RunState.QUEUED, RunState.RUNNING, RunState.SANDBOX_PROVISIONING]:
            instance._record_state_change(RunState.CANCELLED, "Cancelled by user request")
            instance.completed_at = datetime.utcnow().isoformat() + "Z"
            return True
        return False


run_manager = RunExecutionManager()
