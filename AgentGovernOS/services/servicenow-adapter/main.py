"""
AgentGovern OS — ServiceNow Adapter
=====================================
Bridges ServiceNow Flow Designer, Workflow Engine, and Virtual Agent
actions into the AgentGovern OS governance pipeline.

Supports:
  - ServiceNow Flow Designer HTTP actions (outbound REST)
  - IntegrationHub spoke callouts
  - Virtual Agent (VA) topic actions
  - Change Management approval pre-checks
  - ITSM workflow actions (Incident, Change, Problem, Request)

Flow:
  1. ServiceNow Flow Designer / Workflow calls this adapter via HTTP step
  2. Adapter normalises the ServiceNow action payload
  3. SENTINEL evaluates governance policies
  4. Returns a ServiceNow-compatible `result` object for Flow Designer

Run with: uvicorn main:app --host 0.0.0.0 --port 8005 --reload
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

# ── ServiceNow action map ─────────────────────────────────────────────────────
SERVICENOW_ACTION_MAP: dict[str, dict] = {
    # ── Change Management ──
    "RequestEmergencyChange":   {"action_type": "execute_workflow",       "base_risk": 100000.0, "table": "change_request"},
    "ApproveChange":            {"action_type": "approve_expense",        "base_risk": 0.0,      "table": "change_request"},
    "RejectChange":             {"action_type": "modify_data",            "base_risk": 0.0,      "table": "change_request"},
    "AutoApproveStandardChange":{"action_type": "execute_workflow",       "base_risk": 20000.0,  "table": "change_request"},
    "RollbackChange":           {"action_type": "modify_data",            "base_risk": 75000.0,  "table": "change_request"},
    # ── Incident Management ──
    "EscalateIncident":         {"action_type": "escalate",               "base_risk": 0.0,      "table": "incident"},
    "AutoResolveIncident":      {"action_type": "modify_data",            "base_risk": 5000.0,   "table": "incident"},
    "MassCloseIncidents":       {"action_type": "bulk_delete_records",    "base_risk": 30000.0,  "table": "incident"},
    "PagesOnCallEngineer":      {"action_type": "send_communication",     "base_risk": 0.0,      "table": "incident"},
    # ── ITSM / Service Requests ──
    "FulfillServiceRequest":    {"action_type": "execute_workflow",       "base_risk": 5000.0,   "table": "sc_request"},
    "ApproveServiceRequest":    {"action_type": "approve_expense",        "base_risk": 0.0,      "table": "sc_request"},
    "CancelServiceRequest":     {"action_type": "modify_data",            "base_risk": 0.0,      "table": "sc_request"},
    "BulkFulfillRequests":      {"action_type": "execute_workflow",       "base_risk": 50000.0,  "table": "sc_request"},
    # ── Asset & CMDB ──
    "ProvisionAsset":           {"action_type": "provision_compute",      "base_risk": 50000.0,  "table": "alm_asset"},
    "DecommissionAsset":        {"action_type": "destroy_database",       "base_risk": 75000.0,  "table": "alm_asset"},
    "BulkUpdateCMDB":           {"action_type": "bulk_delete_records",    "base_risk": 100000.0, "table": "cmdb_ci"},
    "TransferAssetOwnership":   {"action_type": "modify_system_access",   "base_risk": 20000.0,  "table": "alm_asset"},
    # ── Identity & Access (ServiceNow IAM) ──
    "ProvisionUserAccount":     {"action_type": "modify_system_access",   "base_risk": 25000.0,  "table": "sys_user"},
    "DeprovisionUser":          {"action_type": "modify_system_access",   "base_risk": 25000.0,  "table": "sys_user"},
    "GrantAdminAccess":         {"action_type": "elevate_iam_privilege",  "base_risk": 100000.0, "table": "sys_user_role"},
    "BulkRoleAssignment":       {"action_type": "elevate_iam_privilege",  "base_risk": 100000.0, "table": "sys_user_role"},
    # ── Security Operations ──
    "BlockIPAddress":           {"action_type": "modify_storage_acl",     "base_risk": 10000.0,  "table": "sn_si_incident"},
    "IsolateEndpoint":          {"action_type": "modify_system_access",   "base_risk": 50000.0,  "table": "cmdb_ci_computer"},
    "RunVulnerabilityScan":     {"action_type": "invoke_function",        "base_risk": 0.0,      "table": "sn_vul_entry"},
    "PatchSystem":              {"action_type": "deploy_function",        "base_risk": 30000.0,  "table": "cmdb_ci"},
    # ── Virtual Agent ──
    "VALookupRecord":           {"action_type": "query_data",             "base_risk": 0.0,      "table": "sys_user"},
    "VAUpdateRecord":           {"action_type": "modify_data",            "base_risk": 5000.0,   "table": "incident"},
    "VACreateRequest":          {"action_type": "create_record",          "base_risk": 0.0,      "table": "sc_request"},
}

DEFAULT_ACTION = {"action_type": "unknown_snow_action", "base_risk": 10000.0, "table": "unknown"}


# ── Pydantic models ──────────────────────────────────────────────────────────

class ServiceNowActionRequest(BaseModel):
    """ServiceNow Flow Designer HTTP action payload."""
    action_name: str = Field(..., description="ServiceNow action name, e.g. 'ApproveChange'")
    flow_name: str = Field(default="UnknownFlow", description="ServiceNow Flow or Workflow name")
    instance_url: str = Field(default="", description="ServiceNow instance URL (e.g. https://company.service-now.com)")
    sys_id: str = Field(default="", description="Record sys_id being acted on")
    table_name: str = Field(default="", description="ServiceNow table name (auto-detected if empty)")
    user_sys_id: str = Field(default="", description="sys_id of the user/agent triggering the action")
    parameters: dict[str, Any] = Field(default_factory=dict)
    amount: float = Field(default=0.0, description="Estimated financial impact (INR)")
    currency: str = Field(default="INR")
    record_count: int = Field(default=1, description="Number of affected records")
    priority: str = Field(default="3", description="ServiceNow priority (1=Critical, 5=Planning)")


class ServiceNowGovernanceResponse(BaseModel):
    """AgentGovern OS verdict in ServiceNow Flow Designer format.

    ServiceNow Flow Designer HTTP step reads the `result` field.
    The boolean flags allow direct Flow branching without scripting.
    """
    # ServiceNow Flow Designer output pill names
    result: dict        # Nested result object (Flow Designer output variable)
    # Top-level for IntegrationHub compatibility
    verdict: str
    can_proceed: bool
    governance_timestamp: str


class BatchServiceNowRequest(BaseModel):
    actions: list[ServiceNowActionRequest]


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgentGovern OS — ServiceNow Adapter",
    description=(
        "Governance bridge for ServiceNow Flow Designer, IntegrationHub, "
        "Virtual Agent topic actions, and Change Management workflows."
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
        return {"verdict": "block", "reasoning": "Zero-trust: no registered ServiceNow agent", "confidence": 0.99, "policy_results": []}
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


async def _create_escalation(agent_id: str, context: dict, reason: str, client: httpx.AsyncClient) -> str | None:
    try:
        resp = await client.post(
            f"{GOVERNANCE_API_URL}/api/v1/escalations/",
            json={"agent_id": agent_id, "escalation_reason": reason, "priority": "high", "context_package": context},
            timeout=5.0,
        )
        if resp.status_code == 201:
            return resp.json().get("id")
    except httpx.RequestError:
        pass
    return None


# ── Main endpoint ─────────────────────────────────────────────────────────────

@app.post(
    "/servicenow/governance/evaluate",
    response_model=ServiceNowGovernanceResponse,
    tags=["governance"],
    summary="Govern a ServiceNow Flow Designer action",
)
async def evaluate_snow_action(req: ServiceNowActionRequest) -> ServiceNowGovernanceResponse:
    """Evaluate a ServiceNow action through AgentGovern OS.

    Priority multiplier: Critical (P1) actions carry 5× risk weight.
    Bulk actions carry additional risk proportional to record count.
    """
    request_id = str(uuid.uuid4())
    action_meta = SERVICENOW_ACTION_MAP.get(req.action_name, DEFAULT_ACTION)
    table = req.table_name or action_meta["table"]

    # Priority multiplier (P1=Critical gets highest scrutiny)
    priority_multiplier = {
        "1": 5.0, "2": 3.0, "3": 2.0, "4": 1.5, "5": 1.0,
        "critical": 5.0, "high": 3.0, "medium": 2.0, "low": 1.5, "planning": 1.0,
    }.get(str(req.priority).lower, 2.0)

    amount = req.amount if req.amount > 0 else action_meta["base_risk"]
    if req.record_count > 10:
        amount = max(amount, action_meta["base_risk"] * min(req.record_count / 10, 20))
    amount *= priority_multiplier

    context_package = {
        "environment": "ServiceNow",
        "source": "flow_designer",
        "flow_name": req.flow_name,
        "instance_url": req.instance_url,
        "sys_id": req.sys_id,
        "table_name": table,
        "user_sys_id": req.user_sys_id,
        "record_count": req.record_count,
        "snow_priority": req.priority,
    }

    # Determine agent role from action table
    role_map = {
        "change_request": "itsm_agent",
        "incident": "itsm_agent",
        "sc_request": "itsm_agent",
        "alm_asset": "cloud_sec_ops",
        "cmdb_ci": "cloud_sec_ops",
        "sys_user": "hr_bot",
        "sys_user_role": "cloud_sec_ops",
        "sn_si_incident": "cloud_sec_ops",
    }
    role = role_map.get(table, "btp_agent")

    async with httpx.AsyncClient() as client:
        agent_id = await _find_agent(role, client)
        verdict_data = await _evaluate(
            agent_id,
            {
                "agent_id": agent_id,
                "action": {
                    "action_type": action_meta["action_type"],
                    "amount": amount,
                    "currency": req.currency,
                    "snow_action": req.action_name,
                    "snow_table": table,
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

        escalation_case_id = None
        if verdict == "ESCALATE" and agent_id:
            escalation_case_id = await _create_escalation(
                agent_id,
                {**context_package, "action_name": req.action_name, "amount": amount},
                "AUTHORITY_EXCEEDED" if not violations else "POLICY_VIOLATION",
                client,
            )

    # Build ServiceNow Flow Designer output object
    snow_result = {
        "requestId": request_id,
        "actionName": req.action_name,
        "snowTable": table,
        "verdict": verdict,
        "canProceed": verdict == "APPROVE",
        "requiresApproval": verdict in ("ESCALATE", "BLOCK"),
        "isApproved": verdict == "APPROVE",
        "isBlocked": verdict == "BLOCK",
        "isEscalated": verdict == "ESCALATE",
        "confidence": verdict_data.get("confidence", 0.5),
        "reasoning": verdict_data.get("reasoning", ""),
        "policyViolations": violations,
        "escalationCaseId": escalation_case_id,
        "auditReference": f"AUD-SNOW-{request_id[:8].upper()}",
        # ServiceNow-native decision (matches Change Advisory Board terminology)
        "changeAdvisoryDecision": {
            "APPROVE": "Approved",
            "BLOCK": "Rejected",
            "ESCALATE": "Pending CAB Review",
        }.get(verdict, "Pending CAB Review"),
        "governanceTimestamp": datetime.now(UTC).isoformat(),
    }

    return ServiceNowGovernanceResponse(
        result=snow_result,
        verdict=verdict,
        can_proceed=verdict == "APPROVE",
        governance_timestamp=datetime.now(UTC).isoformat(),
    )


@app.post(
    "/servicenow/governance/batch",
    response_model=list[ServiceNowGovernanceResponse],
    tags=["governance"],
    summary="Batch govern multiple ServiceNow actions",
)
async def batch_evaluate(batch: BatchServiceNowRequest):
    return [await evaluate_snow_action(a) for a in batch.actions]


@app.post(
    "/servicenow/webhook/change",
    tags=["webhooks"],
    summary="Receive a ServiceNow Change Request event for governance pre-check",
)
async def change_request_webhook(request: Request):
    """Webhook called by ServiceNow Change Management flow before CAB approval."""
    body: dict = await request.json()
    change_type = body.get("type", "Normal").lower()
    urgency = body.get("urgency", "3")

    action = "RequestEmergencyChange" if change_type == "emergency" else "AutoApproveStandardChange" if change_type == "standard" else "ApproveChange"

    req = ServiceNowActionRequest(
        action_name=action,
        flow_name="ChangeManagementFlow",
        instance_url=body.get("instanceUrl", ""),
        sys_id=body.get("sysId", ""),
        table_name="change_request",
        user_sys_id=body.get("requestedBy", ""),
        parameters=body,
        amount=float(body.get("estimatedCost", 0) or 0),
        priority=str(urgency),
    )
    return await evaluate_snow_action(req)


@app.get("/servicenow/actions/catalogue", tags=["metadata"])
async def action_catalogue():
    return {
        "count": len(SERVICENOW_ACTION_MAP),
        "actions": [
            {
                "snow_action": name,
                "snow_table": meta["table"],
                "governance_action_type": meta["action_type"],
                "base_risk_inr": meta["base_risk"],
                "risk_tier": "critical" if meta["base_risk"] >= 75000 else "high" if meta["base_risk"] >= 30000 else "medium" if meta["base_risk"] >= 5000 else "low",
            }
            for name, meta in SERVICENOW_ACTION_MAP.items()
        ],
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "AgentGovern OS — ServiceNow Adapter",
        "version": "1.0.0",
        "status": "operational",
        "governance_api": GOVERNANCE_API_URL,
        "supported_actions": len(SERVICENOW_ACTION_MAP),
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
