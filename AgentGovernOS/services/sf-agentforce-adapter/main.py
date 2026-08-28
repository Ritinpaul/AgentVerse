"""
AgentGovern OS — Salesforce Agentforce Adapter
===============================================
Bridges Salesforce Agentforce AI agent actions into the AgentGovern OS
governance pipeline.

Supports:
  - Agentforce Agent Actions (Einstein Copilot, Agentforce for Sales/Service)
  - Platform Events and Change Data Capture triggers
  - Apex callout-triggered governance checks
  - Flow-triggered HTTP callouts from Salesforce Flow Builder

Flow:
  1. Salesforce Apex / Flow sends an HTTP callout to this adapter
  2. Adapter normalises the Agentforce action into an AgentGovern request
  3. SENTINEL evaluates policies; Prophecy Engine runs where triggered
  4. Adapter returns a Salesforce-compatible JSON response for Flow/Apex

Run with: uvicorn main:app --host 0.0.0.0 --port 8004 --reload
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

GOVERNANCE_API_URL = "http://localhost:8000"

# ── Agentforce action → AgentGovern action mapping ───────────────────────────
AGENTFORCE_ACTION_MAP: dict[str, dict] = {
    # ── Sales Cloud ──
    "UpdateOpportunityStage":   {"action_type": "modify_deal_stage",       "base_risk": 5000.0,  "object": "Opportunity"},
    "CreateQuote":              {"action_type": "issue_discount",           "base_risk": 0.0,     "object": "Quote"},
    "ApproveDiscount":          {"action_type": "issue_discount",           "base_risk": 0.0,     "object": "Quote"},
    "CloseOpportunity":         {"action_type": "modify_deal_stage",        "base_risk": 10000.0, "object": "Opportunity"},
    "BulkUpdateLeadStatus":     {"action_type": "bulk_delete_records",      "base_risk": 30000.0, "object": "Lead"},
    "AssignTerritoryOwner":     {"action_type": "modify_system_access",     "base_risk": 10000.0, "object": "Territory"},
    # ── Service Cloud ──
    "EscalateCase":             {"action_type": "escalate",                 "base_risk": 0.0,     "object": "Case"},
    "ResolveCase":              {"action_type": "modify_data",              "base_risk": 0.0,     "object": "Case"},
    "RefundCustomer":           {"action_type": "process_refund",           "base_risk": 0.0,     "object": "Payment"},
    "SendSurvey":               {"action_type": "send_communication",       "base_risk": 0.0,     "object": "Survey"},
    "MergeContacts":            {"action_type": "bulk_merge_records",       "base_risk": 20000.0, "object": "Contact"},
    "DeleteDuplicateLeads":     {"action_type": "bulk_delete_records",      "base_risk": 50000.0, "object": "Lead"},
    # ── Marketing Cloud ──
    "LaunchCampaign":           {"action_type": "execute_workflow",         "base_risk": 5000.0,  "object": "Campaign"},
    "ExportContactList":        {"action_type": "export_sensitive_data",    "base_risk": 50000.0, "object": "Contact"},
    "BulkEmailSend":            {"action_type": "send_communication",       "base_risk": 10000.0, "object": "EmailMessage"},
    "UpdatePricebook":          {"action_type": "bulk_update_prices",       "base_risk": 30000.0, "object": "PricebookEntry"},
    # ── Platform / Data ──
    "RunApexClass":             {"action_type": "deploy_function",          "base_risk": 50000.0, "object": "ApexClass"},
    "DataExport":               {"action_type": "export_sensitive_data",    "base_risk": 100000.0,"object": "DataExport"},
    "CreateUser":               {"action_type": "modify_system_access",     "base_risk": 25000.0, "object": "User"},
    "DeactivateUser":           {"action_type": "modify_system_access",     "base_risk": 25000.0, "object": "User"},
    "AssignPermissionSet":      {"action_type": "elevate_iam_privilege",    "base_risk": 75000.0, "object": "PermissionSet"},
    "TriggerFlow":              {"action_type": "execute_workflow",         "base_risk": 5000.0,  "object": "Flow"},
}

DEFAULT_ACTION = {"action_type": "unknown_sf_action", "base_risk": 10000.0, "object": "Unknown"}


# ── Pydantic models ──────────────────────────────────────────────────────────

class AgentforceActionRequest(BaseModel):
    """Salesforce Agentforce / Apex callout governance request."""
    action_name: str = Field(..., description="Agentforce action name, e.g. 'UpdateOpportunityStage'")
    agent_name: str = Field(default="EinsteinCopilot", description="Name of the Salesforce AI agent")
    org_id: str = Field(default="", description="Salesforce Org ID (18-char)")
    user_id: str = Field(default="", description="Salesforce User ID of the requesting user")
    record_id: str = Field(default="", description="Salesforce Record ID being acted on")
    parameters: dict[str, Any] = Field(default_factory=dict)
    amount: float = Field(default=0.0, description="Financial amount if applicable (INR)")
    currency: str = Field(default="INR")
    record_count: int = Field(default=1, description="Number of records affected (for bulk ops)")


class AgentforceGovernanceResponse(BaseModel):
    """AgentGovern OS verdict in Salesforce-compatible format."""
    # Salesforce Apex / Flow can read these directly
    request_id: str
    action_name: str
    salesforce_object: str
    verdict: str
    can_proceed: bool
    requires_approval: bool
    confidence: float
    reasoning: str
    policy_violations: list[str]
    # For Salesforce Flow: boolean flags the Flow can route on
    is_approved: bool
    is_blocked: bool
    is_escalated: bool
    # ECLIPSE escalation case ID (if escalated)
    escalation_case_id: str | None
    governance_timestamp: str
    audit_reference: str


class BatchAgentforceRequest(BaseModel):
    actions: list[AgentforceActionRequest]


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgentGovern OS — Salesforce Agentforce Adapter",
    description=(
        "Governance bridge for Salesforce Agentforce AI agents, Einstein Copilot, "
        "Apex callouts, and Salesforce Flow Builder HTTP actions."
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
    if not agent_id:
        return {"verdict": "block", "reasoning": "Zero-trust: no registered Agentforce agent", "confidence": 0.99, "policy_results": []}
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
    return {"verdict": "escalate", "reasoning": "Governance API unreachable", "confidence": 0.5, "policy_results": []}


async def _create_escalation(
    agent_id: str, case_context: dict, reason: str, client: httpx.AsyncClient
) -> str | None:
    try:
        resp = await client.post(
            f"{GOVERNANCE_API_URL}/api/v1/escalations/",
            json={
                "agent_id": agent_id,
                "escalation_reason": reason,
                "priority": "medium",
                "context_package": case_context,
            },
            timeout=5.0,
        )
        if resp.status_code == 201:
            return resp.json().get("id")
    except httpx.RequestError:
        pass
    return None


# ── Main endpoint ─────────────────────────────────────────────────────────────

@app.post(
    "/agentforce/governance/evaluate",
    response_model=AgentforceGovernanceResponse,
    tags=["governance"],
    summary="Govern a Salesforce Agentforce action",
)
async def evaluate_agentforce_action(req: AgentforceActionRequest) -> AgentforceGovernanceResponse:
    """Evaluate a Salesforce Agentforce action through AgentGovern OS.

    Calculates effective risk from:
      - Base risk of the action type
      - Financial amount (if provided)
      - Record count multiplier (bulk ops are higher risk)
    """
    request_id = str(uuid.uuid4())
    action_meta = AGENTFORCE_ACTION_MAP.get(req.action_name, DEFAULT_ACTION)

    # Risk calculation
    amount = req.amount if req.amount > 0 else action_meta["base_risk"]
    if req.record_count > 100:
        amount = max(amount, action_meta["base_risk"] * min(req.record_count / 100, 10))

    context_package = {
        "environment": "Salesforce Cloud",
        "source": "agentforce",
        "agent_name": req.agent_name,
        "org_id": req.org_id,
        "user_id": req.user_id,
        "record_id": req.record_id,
        "record_count": req.record_count,
        "salesforce_object": action_meta["object"],
    }

    async with httpx.AsyncClient() as client:
        agent_id = await _find_agent("crm_agent", client)
        verdict_data = await _evaluate(
            agent_id,
            {
                "agent_id": agent_id,
                "action": {
                    "action_type": action_meta["action_type"],
                    "amount": amount,
                    "currency": req.currency,
                    "agentforce_action": req.action_name,
                    "record_count": req.record_count,
                    "parameters": req.parameters,
                },
                "context": context_package,
            },
            client,
        )

        verdict = verdict_data.get("verdict", "escalate").upper()
        violations = [
            r["policy_code"]
            for r in verdict_data.get("policy_results", [])
            if not r.get("passed", True)
        ]

        # Auto-create ECLIPSE escalation case when ESCALATE verdict
        escalation_case_id = None
        if verdict == "ESCALATE" and agent_id:
            escalation_case_id = await _create_escalation(
                agent_id,
                {**context_package, "action_name": req.action_name, "amount": amount},
                "POLICY_VIOLATION" if violations else "AUTHORITY_EXCEEDED",
                client,
            )

    return AgentforceGovernanceResponse(
        request_id=request_id,
        action_name=req.action_name,
        salesforce_object=action_meta["object"],
        verdict=verdict,
        can_proceed=verdict == "APPROVE",
        requires_approval=verdict in ("ESCALATE", "BLOCK"),
        confidence=verdict_data.get("confidence", 0.5),
        reasoning=verdict_data.get("reasoning", ""),
        policy_violations=violations,
        is_approved=verdict == "APPROVE",
        is_blocked=verdict == "BLOCK",
        is_escalated=verdict == "ESCALATE",
        escalation_case_id=escalation_case_id,
        governance_timestamp=datetime.now(UTC).isoformat(),
        audit_reference=f"AUD-SF-{request_id[:8].upper()}",
    )


@app.post(
    "/agentforce/governance/batch",
    response_model=list[AgentforceGovernanceResponse],
    tags=["governance"],
    summary="Batch govern multiple Agentforce actions",
)
async def batch_evaluate(batch: BatchAgentforceRequest):
    return [await evaluate_agentforce_action(a) for a in batch.actions]


@app.post(
    "/agentforce/webhook/platform-event",
    tags=["webhooks"],
    summary="Receive a Salesforce Platform Event for governance",
)
async def receive_platform_event(request: Request):
    """Receive a Salesforce Platform Event (Change Data Capture / custom event)
    and route it through governance evaluation.
    """
    body: dict = await request.json()
    schema_name = body.get("schema", "UnknownEvent__e")
    payload = body.get("payload", {})
    change_type = body.get("changeType", "UPDATE")

    action_map = {
        "CREATE": "create_record",
        "UPDATE": "modify_data",
        "DELETE": "delete_data",
        "UNDELETE": "modify_data",
        "GAP_CREATE": "create_record",
        "GAP_DELETE": "delete_data",
    }

    req = AgentforceActionRequest(
        action_name=action_map.get(change_type, "modify_data"),
        agent_name="PlatformEventAgent",
        org_id=payload.get("OrgId__c", ""),
        parameters=payload,
        amount=float(payload.get("Amount__c", 0) or 0),
    )
    return await evaluate_agentforce_action(req)


@app.get("/agentforce/actions/catalogue", tags=["metadata"])
async def action_catalogue():
    return {
        "count": len(AGENTFORCE_ACTION_MAP),
        "actions": [
            {
                "agentforce_action": name,
                "salesforce_object": meta["object"],
                "governance_action_type": meta["action_type"],
                "base_risk_inr": meta["base_risk"],
                "risk_tier": "high" if meta["base_risk"] >= 50000 else "medium" if meta["base_risk"] >= 5000 else "low",
            }
            for name, meta in AGENTFORCE_ACTION_MAP.items()
        ],
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "AgentGovern OS — Salesforce Agentforce Adapter",
        "version": "1.0.0",
        "status": "operational",
        "governance_api": GOVERNANCE_API_URL,
        "supported_actions": len(AGENTFORCE_ACTION_MAP),
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health():
    gov_status = "unreachable"
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{GOVERNANCE_API_URL}/health", timeout=3.0)
            if r.status_code == 200:
                gov_status = "connected"
    except Exception:
        pass
    return {"status": "ok", "governance_api": gov_status}
