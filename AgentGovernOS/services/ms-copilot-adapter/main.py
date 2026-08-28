"""
AgentGovern OS — Microsoft Copilot Studio Adapter
==================================================
Bridges Microsoft Copilot Studio / Power Platform agent actions
into the AgentGovern OS governance pipeline.

Supports:
  - Power Automate custom connector invocations from Copilot Studio topics
  - Azure AI Agent Service action calls (via OpenAI-compatible format)
  - Microsoft 365 Copilot extensibility plugins
  - Teams AI Library bot actions

Flow:
  1. Copilot Studio calls this adapter via a Power Automate HTTP connector
  2. Adapter normalises the action into an AgentGovern ActionEvaluationRequest
  3. SENTINEL evaluates the action against active governance policies
  4. Adapter returns a Power Platform-compatible governance verdict

Run with: uvicorn main:app --host 0.0.0.0 --port 8003 --reload
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

GOVERNANCE_API_URL = "http://localhost:8000"

# ── Action risk catalogue (Copilot Studio action → governance action_type) ───
COPILOT_ACTION_MAP: dict[str, dict] = {
    # ── Data operations ──
    "GetRecords":           {"action_type": "query_data",          "base_risk": 0.0},
    "GetRecord":            {"action_type": "query_data",          "base_risk": 0.0},
    "SearchRecords":        {"action_type": "query_data",          "base_risk": 0.0},
    "CreateRecord":         {"action_type": "create_record",       "base_risk": 5000.0},
    "UpdateRecord":         {"action_type": "modify_data",         "base_risk": 5000.0},
    "DeleteRecord":         {"action_type": "delete_data",         "base_risk": 50000.0},
    "BulkDelete":           {"action_type": "bulk_delete_records", "base_risk": 100000.0},
    # ── Finance / ERP actions ──
    "ApproveExpense":       {"action_type": "approve_expense",     "base_risk": 0.0},
    "SubmitInvoice":        {"action_type": "approve_payment",     "base_risk": 0.0},
    "TransferFunds":        {"action_type": "wire_transfer",       "base_risk": 0.0},
    "GenerateQuote":        {"action_type": "issue_discount",      "base_risk": 0.0},
    # ── Identity & access ──
    "AssignRole":           {"action_type": "elevate_iam_privilege","base_risk": 75000.0},
    "RevokeAccess":         {"action_type": "modify_system_access", "base_risk": 30000.0},
    "ResetPassword":        {"action_type": "modify_system_access", "base_risk": 10000.0},
    # ── Communication ──
    "SendEmail":            {"action_type": "send_communication",  "base_risk": 0.0},
    "SendTeamsMessage":     {"action_type": "send_communication",  "base_risk": 0.0},
    "BroadcastMessage":     {"action_type": "send_communication",  "base_risk": 5000.0},
    # ── Document & file operations ──
    "UploadFile":           {"action_type": "create_record",       "base_risk": 0.0},
    "DeleteFile":           {"action_type": "delete_data",         "base_risk": 20000.0},
    "ShareDocument":        {"action_type": "export_sensitive_data","base_risk": 10000.0},
    "ExportData":           {"action_type": "export_sensitive_data","base_risk": 50000.0},
    # ── AI & automation ──
    "InvokePlugin":         {"action_type": "invoke_function",     "base_risk": 5000.0},
    "TriggerFlow":          {"action_type": "execute_workflow",    "base_risk": 5000.0},
    "RunScript":            {"action_type": "deploy_function",     "base_risk": 30000.0},
}

DEFAULT_ACTION = {"action_type": "unknown_action", "base_risk": 10000.0}


# ── Pydantic models ──────────────────────────────────────────────────────────

class CopilotActionRequest(BaseModel):
    """Power Platform / Copilot Studio action invocation."""
    action_name: str = Field(..., description="Copilot Studio action name, e.g. 'ApproveExpense'")
    connector_id: str = Field(default="agentgovern-connector")
    bot_name: str = Field(default="CopilotBot", description="Name of the Copilot agent")
    user_id: str = Field(default="", description="Microsoft 365 user UPN or object ID")
    tenant_id: str = Field(default="", description="Azure AD / Entra tenant ID")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action input parameters")
    amount: float = Field(default=0.0, description="Financial amount if applicable (INR)")
    currency: str = Field(default="INR")
    environment: str = Field(
        default="Microsoft Cloud",
        description="Power Platform environment name",
    )


class CopilotGovernanceResponse(BaseModel):
    """AgentGovern OS verdict in Power Platform-compatible format."""
    request_id: str
    action_name: str
    bot_name: str
    verdict: str
    confidence: float
    reasoning: str
    policy_violations: list[str]
    # Power Automate / Copilot response fields
    can_proceed: bool
    requires_approval: bool
    approval_instructions: str | None
    governance_timestamp: str
    audit_reference: str


class BatchCopilotRequest(BaseModel):
    actions: list[CopilotActionRequest]


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgentGovern OS — Microsoft Copilot Studio Adapter",
    description=(
        "Governance bridge for Microsoft Copilot Studio, Power Automate, "
        "Azure AI Agents, and Microsoft 365 Copilot extensibility plugins."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _find_agent(role: str, client: httpx.AsyncClient) -> str | None:
    try:
        resp = await client.get(
            f"{GOVERNANCE_API_URL}/api/v1/agents/",
            params={"role": role, "status_filter": "active", "limit": 1},
            timeout=5.0,
        )
        if resp.status_code == 200:
            agents = resp.json().get("agents", [])
            if agents:
                return agents[0]["id"]
    except httpx.RequestError:
        pass
    return None


async def _evaluate(agent_id: str | None, payload: dict, client: httpx.AsyncClient) -> dict:
    default = {"verdict": "escalate", "reasoning": "Governance API unreachable", "confidence": 0.5, "policy_results": []}
    if not agent_id:
        return {"verdict": "block", "reasoning": "Zero-trust: no registered agent for Copilot role", "confidence": 0.99, "policy_results": []}
    try:
        resp = await client.post(
            f"{GOVERNANCE_API_URL}/api/v1/sentinel/evaluate",
            json=payload,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
    except httpx.RequestError:
        pass
    return default


# ── Main endpoint ─────────────────────────────────────────────────────────────

@app.post(
    "/copilot/governance/evaluate",
    response_model=CopilotGovernanceResponse,
    tags=["governance"],
    summary="Govern a Copilot Studio action invocation",
)
async def evaluate_copilot_action(req: CopilotActionRequest) -> CopilotGovernanceResponse:
    """Evaluate a Microsoft Copilot Studio action through AgentGovern OS."""
    request_id = str(uuid.uuid4())
    action_meta = COPILOT_ACTION_MAP.get(req.action_name, DEFAULT_ACTION)
    effective_amount = req.amount if req.amount > 0 else action_meta["base_risk"]

    async with httpx.AsyncClient() as client:
        agent_id = await _find_agent("copilot_agent", client)
        verdict_data = await _evaluate(
            agent_id,
            {
                "agent_id": agent_id,
                "action": {
                    "action_type": action_meta["action_type"],
                    "amount": effective_amount,
                    "currency": req.currency,
                    "copilot_action": req.action_name,
                    "parameters": req.parameters,
                },
                "context": {
                    "environment": req.environment,
                    "source": "ms_copilot_studio",
                    "bot_name": req.bot_name,
                    "user_id": req.user_id,
                    "tenant_id": req.tenant_id,
                },
            },
            client,
        )

    verdict = verdict_data.get("verdict", "escalate").upper()
    can_proceed = verdict == "APPROVE"
    requires_approval = verdict in ("ESCALATE", "BLOCK")

    approval_map = {
        "APPROVE": None,
        "BLOCK": "This action has been blocked by enterprise governance policy. Contact your administrator.",
        "ESCALATE": (
            "This action requires human approval. "
            "A governance review request has been submitted. "
            "You will be notified once reviewed."
        ),
    }

    return CopilotGovernanceResponse(
        request_id=request_id,
        action_name=req.action_name,
        bot_name=req.bot_name,
        verdict=verdict,
        confidence=verdict_data.get("confidence", 0.5),
        reasoning=verdict_data.get("reasoning", ""),
        policy_violations=[
            r["policy_code"]
            for r in verdict_data.get("policy_results", [])
            if not r.get("passed", True)
        ],
        can_proceed=can_proceed,
        requires_approval=requires_approval,
        approval_instructions=approval_map.get(verdict),
        governance_timestamp=datetime.now(UTC).isoformat(),
        audit_reference=f"AUD-{request_id[:8].upper()}",
    )


@app.post(
    "/copilot/governance/batch",
    response_model=list[CopilotGovernanceResponse],
    tags=["governance"],
    summary="Batch govern multiple Copilot Studio actions",
)
async def batch_evaluate(batch: BatchCopilotRequest):
    """Process multiple Copilot Studio action requests in sequence."""
    return [await evaluate_copilot_action(action) for action in batch.actions]


@app.get("/copilot/actions/catalogue", tags=["metadata"])
async def list_action_catalogue():
    """Return the full Copilot Studio action catalogue with risk classifications."""
    return {
        "count": len(COPILOT_ACTION_MAP),
        "actions": [
            {
                "copilot_action": name,
                "governance_action_type": meta["action_type"],
                "base_risk_inr": meta["base_risk"],
                "risk_tier": (
                    "high" if meta["base_risk"] >= 50000
                    else "medium" if meta["base_risk"] >= 5000
                    else "low"
                ),
            }
            for name, meta in COPILOT_ACTION_MAP.items()
        ],
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "AgentGovern OS — Microsoft Copilot Studio Adapter",
        "version": "1.0.0",
        "status": "operational",
        "governance_api": GOVERNANCE_API_URL,
        "supported_actions": len(COPILOT_ACTION_MAP),
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health():
    gov_status = "unreachable"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GOVERNANCE_API_URL}/health", timeout=3.0)
            if resp.status_code == 200:
                gov_status = "connected"
    except Exception:
        pass
    return {"status": "ok", "governance_api": gov_status, "supported_actions": len(COPILOT_ACTION_MAP)}
