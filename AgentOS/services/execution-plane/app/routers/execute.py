"""
app/routers/execute.py

Execution Plane API Endpoints with full Run State Machine & Step Telemetry.
"""

import re
import os
from fastapi import APIRouter, HTTPException, Header, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
from app.sandbox.runner import sandbox
from app.sandbox.run_state_machine import run_manager
from app.sandbox.terminal_bridge import terminal_manager

router = APIRouter(prefix="/execute", tags=["execution"])

# Shell metacharacters regex for entrypoint sanitization
SAFE_ENTRYPOINT_REGEX = re.compile(r"^[a-zA-Z0-9_./\- ]+$")
FORBIDDEN_PATTERNS = [";", "&&", "||", "|", ">", "<", "$", "`", "(", ")", "sudo", "eval", "exec"]


class LegacyRunRequest(BaseModel):
    agent_id: str
    entrypoint: str
    env_vars: Dict[str, str]

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint(cls, v: str) -> str:
        v_clean = v.strip()
        if not SAFE_ENTRYPOINT_REGEX.match(v_clean) or any(p in v_clean for p in FORBIDDEN_PATTERNS):
            raise ValueError("Invalid or unsafe entrypoint command detected.")
        return v_clean


class V1RunRequest(BaseModel):
    agent_id: str = Field(..., alias="agentId")
    manifest: Dict[str, Any]
    input_text: Optional[str] = "Execute workload"
    simulate_tool_calls: Optional[List[Dict[str, Any]]] = None

    model_config = {"populate_by_name": True}


def verify_service_token(x_service_token: Optional[str] = Header(None)):
    expected_token = os.getenv("NUUVIXX_API_KEY", "dev-nuuvixx-svc-key-2026")
    env = os.getenv("ENVIRONMENT", "local")
    if env != "local" and x_service_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing inter-service authentication token."
        )


# ── V1 Execution State Machine API Endpoints ─────────────────────────────────

@router.post("/v1/run")
async def start_v1_run(req: V1RunRequest, x_service_token: Optional[str] = Header(None)):
    """
    Executes a run using the full Execution Plane State Machine & Runtime Policy Interceptor.
    """
    verify_service_token(x_service_token)
    try:
        run_instance = run_manager.create_run(agent_id=req.agent_id, manifest=req.manifest)

        # Run state machine loop
        final_status = run_instance.run_execution(simulate_tool_calls=req.simulate_tool_calls)

        return {
            "runId": run_instance.run_id,
            "agentId": run_instance.agent_id,
            "status": final_status,
            "policyVerdict": run_instance.policy_verdict,
            "denialReason": run_instance.denial_reason,
            "cumulativeCostUsd": run_instance.cumulative_cost_usd,
            "totalSteps": len(run_instance.steps),
            "createdAt": run_instance.created_at,
            "completedAt": run_instance.completed_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


@router.get("/v1/runs/{run_id}/status")
async def get_run_status(run_id: str, x_service_token: Optional[str] = Header(None)):
    """
    Gets state machine phase history, timing, policy verdict, and cumulative cost.
    """
    verify_service_token(x_service_token)
    run_instance = run_manager.get_run(run_id)
    if not run_instance:
        raise HTTPException(status_code=404, detail="Run instance not found")

    return {
        "runId": run_instance.run_id,
        "agentId": run_instance.agent_id,
        "status": run_instance.status,
        "policyVerdict": run_instance.policy_verdict,
        "denialReason": run_instance.denial_reason,
        "cumulativeCostUsd": run_instance.cumulative_cost_usd,
        "stateHistory": run_instance.state_history,
        "createdAt": run_instance.created_at,
        "startedAt": run_instance.started_at,
        "completedAt": run_instance.completed_at
    }


@router.get("/v1/runs/{run_id}/steps")
async def get_run_steps(run_id: str, x_service_token: Optional[str] = Header(None)):
    """
    Gets structured append-only step telemetry stream for a run.
    """
    verify_service_token(x_service_token)
    run_instance = run_manager.get_run(run_id)
    if not run_instance:
        raise HTTPException(status_code=404, detail="Run instance not found")

    return {
        "runId": run_instance.run_id,
        "agentId": run_instance.agent_id,
        "totalSteps": len(run_instance.steps),
        "steps": [step.to_dict() for step in run_instance.steps]
    }


@router.post("/v1/runs/{run_id}/cancel")
async def cancel_v1_run(run_id: str, x_service_token: Optional[str] = Header(None)):
    """
    Cancels a running agent and transitions state machine to CANCELLED.
    """
    verify_service_token(x_service_token)
    success = run_manager.cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run is not in a cancellable state")
    return {"status": "CANCELLED", "runId": run_id}


# ── Legacy Endpoints ──────────────────────────────────────────────────────────

@router.post("/run")
async def run_agent(req: LegacyRunRequest, x_service_token: Optional[str] = Header(None)):
    verify_service_token(x_service_token)
    try:
        sandbox.start_execution(req.agent_id, req.entrypoint, req.env_vars)
        return {"status": "started", "agent_id": req.agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: str, x_service_token: Optional[str] = Header(None)):
    verify_service_token(x_service_token)
    success = sandbox.stop_execution(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent is not currently running.")
    return {"status": "stopped", "agent_id": agent_id}


# ── Interactive Sandboxed PTY WebSocket Bridge ──────────────────────────────

@router.websocket("/ws/terminal/{agent_id}")
async def terminal_websocket_endpoint(websocket: WebSocket, agent_id: str):
    """
    WebSocket endpoint for bidirectional interactive PTY terminal streaming.
    Connects xterm.js in the Web IDE directly to the agent's sandboxed microvm or container session.
    """
    await terminal_manager.handle_connection(agent_id, websocket)

