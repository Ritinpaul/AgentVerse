"""
AgentGovern OS — SAP BTP Adapter Service
=========================================
Bridges enterprise SAP Business Technology Platform events
into the AgentGovern OS governance pipeline.

Supports:
- SAP S/4HANA business workflow events (procurement, finance, HR)
- SAP BTP CAP (Cloud Application Programming) event webhooks
- SAP Alert Notification Service push events
- SAP Integration Suite iFlow event forwarding

The adapter:
1. Receives SAP BTP CloudEvents (v1.0 spec)
2. Normalizes them into AgentGovern OS ActionEvaluationRequest
3. Forwards to SENTINEL for policy evaluation
4. Returns SAP-compatible governance verdict
5. Logs decision to ANCESTOR audit chain

Run with: uvicorn sap_btp_adapter.main:app --host 0.0.0.0 --port 8002 --reload
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────

GOVERNANCE_API_URL = "http://localhost:8000"  # AgentGovern OS Control Plane

# Universal Enterprise Event Map
# Maps event types from ANY system into AgentGovern OS action definitions.
# Supported systems: SAP S/4HANA, SAP BTP, Stripe, AWS CloudTrail, GitHub, Salesforce
UNIVERSAL_EVENT_MAP = {
    # ─── SAP S/4HANA Finance Events ───────────────────────────────────────────
    "sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1": {
        "action_type": "approve_purchase",
        "agent_role": "fi_analyst",
        "amount_field": "NetAmount",
        "currency_field": "DocumentCurrency",
    },
    "sap.s4.beh.paymentAdvice.v1.PaymentAdvice.Posted.v1": {
        "action_type": "approve_payment",
        "agent_role": "fi_analyst",
        "amount_field": "Amount",
        "currency_field": "Currency",
    },
    # ─── SAP S/4HANA HR Events ────────────────────────────────────────────────
    "sap.s4.beh.employee.v1.Employee.Onboarded.v1": {
        "action_type": "access_pii",
        "agent_role": "hr_bot",
        "amount_field": None,
        "currency_field": None,
    },
    "sap.s4.beh.employee.v1.Employee.Terminated.v1": {
        "action_type": "modify_system_access",
        "agent_role": "hr_bot",
        "amount_field": None,
        "currency_field": None,
    },
    # ─── SAP S/4HANA Sales Events ─────────────────────────────────────────────
    "sap.s4.beh.salesorder.v1.SalesOrder.Created.v1": {
        "action_type": "issue_discount",
        "agent_role": "sales_rep",
        "amount_field": "TotalNetAmount",
        "currency_field": "TransactionCurrency",
    },
    # ─── SAP BTP Alert Notification ───────────────────────────────────────────
    "com.sap.alert.notification.v1.AlertNotification.Triggered.v1": {
        "action_type": "threshold_breach",
        "agent_role": "edge_sensor",
        "amount_field": "thresholdValue",
        "currency_field": None,
    },
    # ─── SAP BTP Workflow ─────────────────────────────────────────────────────
    "com.sap.btp.workflow.v1.WorkflowInstance.Started.v1": {
        "action_type": "execute_workflow",
        "agent_role": "btp_agent",
        "amount_field": None,
        "currency_field": None,
    },
    # ─── Stripe Payment Events ─────────────────────────────────────────────────
    # These map to the billing_agent role — unregistered by default (BLOCK)
    "stripe.charge.refunded.v1": {
        "action_type": "process_refund",
        "agent_role": "billing_agent",
        "amount_field": "amount",
        "currency_field": "currency",
    },
    "stripe.customer.subscription.deleted.v1": {
        "action_type": "cancel_subscription",
        "agent_role": "billing_agent",
        "amount_field": None,
        "currency_field": None,
    },
    "stripe.payout.created.v1": {
        "action_type": "initiate_payout",
        "agent_role": "billing_agent",
        "amount_field": "amount",
        "currency_field": "currency",
    },
    "stripe.invoice.payment_succeeded.v1": {
        "action_type": "record_payment",
        "agent_role": "billing_agent",
        "amount_field": "amount",
        "currency_field": "currency",
    },
    # ─── AWS CloudTrail Events ─────────────────────────────────────────────────
    # These map to the cloud_sec_ops role — unregistered by default (BLOCK)
    "aws.cloudtrail.RunInstances.v1": {
        "action_type": "provision_compute",
        "agent_role": "cloud_sec_ops",
        "amount_field": "estimatedHourlyCost",
        "currency_field": None,
    },
    "aws.cloudtrail.PutBucketAcl.v1": {
        "action_type": "modify_storage_acl",
        "agent_role": "cloud_sec_ops",
        "amount_field": None,
        "currency_field": None,
    },
    "aws.cloudtrail.AttachUserPolicy.v1": {
        "action_type": "elevate_iam_privilege",
        "agent_role": "cloud_sec_ops",
        "amount_field": None,
        "currency_field": None,
    },
    "aws.cloudtrail.DeleteDBInstance.v1": {
        "action_type": "destroy_database",
        "agent_role": "cloud_sec_ops",
        "amount_field": None,
        "currency_field": None,
    },
    "aws.cloudtrail.UpdateFunctionCode.v1": {
        "action_type": "deploy_function",
        "agent_role": "cloud_sec_ops",
        "amount_field": None,
        "currency_field": None,
    },
    "aws.cloudwatch.alarm.triggered.v1": {
        "action_type": "auto_scale_infra",
        "agent_role": "cloud_sec_ops",
        "amount_field": None,
        "currency_field": None,
    },
    "aws.cloudtrail.InvokeFunction.v1": {
        "action_type": "invoke_function",
        "agent_role": "cloud_sec_ops",
        "amount_field": None,
        "currency_field": None,
    },
    # ─── GitHub DevOps Events ──────────────────────────────────────────────────
    # These map to the devops_agent role — unregistered by default (BLOCK)
    "github.push.force.v1": {
        "action_type": "force_push_protected_branch",
        "agent_role": "devops_agent",
        "amount_field": None,
        "currency_field": None,
    },
    "github.secret_scanning_alert.created.v1": {
        "action_type": "secret_exposure",
        "agent_role": "devops_agent",
        "amount_field": None,
        "currency_field": None,
    },
    "github.installation.created.v1": {
        "action_type": "install_third_party_app",
        "agent_role": "devops_agent",
        "amount_field": None,
        "currency_field": None,
    },
    "github.repository.created.v1": {
        "action_type": "create_repository",
        "agent_role": "devops_agent",
        "amount_field": None,
        "currency_field": None,
    },
    "github.pull_request.auto_merged.v1": {
        "action_type": "auto_merge_pr",
        "agent_role": "devops_agent",
        "amount_field": None,
        "currency_field": None,
    },
    "github.workflow.modified.v1": {
        "action_type": "modify_cicd_pipeline",
        "agent_role": "devops_agent",
        "amount_field": None,
        "currency_field": None,
    },
    # ─── Salesforce CRM Events ─────────────────────────────────────────────────
    # These map to the crm_agent role — unregistered by default (BLOCK)
    "salesforce.lead.bulk_delete.v1": {
        "action_type": "bulk_delete_records",
        "agent_role": "crm_agent",
        "amount_field": "recordCount",
        "currency_field": None,
    },
    "salesforce.data.export.v1": {
        "action_type": "export_sensitive_data",
        "agent_role": "crm_agent",
        "amount_field": "rowCount",
        "currency_field": None,
    },
    "salesforce.opportunity.stage_changed.v1": {
        "action_type": "modify_deal_stage",
        "agent_role": "crm_agent",
        "amount_field": "dealValue",
        "currency_field": None,
    },
    "salesforce.contact.merged.v1": {
        "action_type": "bulk_merge_records",
        "agent_role": "crm_agent",
        "amount_field": "totalRecordsMerged",
        "currency_field": None,
    },
    "salesforce.pricebook.bulk_update.v1": {
        "action_type": "bulk_update_prices",
        "agent_role": "crm_agent",
        "amount_field": "productCount",
        "currency_field": None,
    },
}

# Backwards-compat alias used in tests
SAP_EVENT_MAP = UNIVERSAL_EVENT_MAP


# ─── Pydantic Models ───────────────────────────────────────────────────────────

class SAPCloudEvent(BaseModel):
    """SAP BTP CloudEvent (CloudEvents 1.0 spec)."""
    specversion: str = "1.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4))
    source: str  # e.g. "/sap/s4hana/prod/purchaseorder"
    type: str    # e.g. "sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1"
    datacontenttype: str = "application/json"
    time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat)
    data: dict[str, Any] = Field(default_factory=dict)
    # SAP-specific extensions
    sap_source_system: str | None = None  # e.g. "S4H-PROD-001"
    sap_tenant_id: str | None = None


class SAPGovernanceVerdictResponse(BaseModel):
    """AgentGovern OS verdict in SAP-compatible format."""
    event_id: str
    sap_source: str
    sap_event_type: str
    agent_assigned: str      # which AgentGovern OS agent handled this
    verdict: str             # "APPROVE" | "BLOCK" | "ESCALATE"
    confidence: float
    reasoning: str
    policy_violations: list[str]
    audit_hash: str | None = None
    governance_timestamp: str
    # SAP workflow integration fields
    workflow_decision: str   # "APPROVE" | "REJECT" | "DELEGATE"
    requires_human_review: bool
    escalation_contact: str | None = None


class BatchSAPEventRequest(BaseModel):
    """Batch processing for multiple SAP events."""
    events: list[SAPCloudEvent]


# ─── FastAPI Application ──────────────────────────────────────────────────────

app = FastAPI(
    title="AgentGovern OS — SAP BTP Adapter",
    description=(
        "Enterprise bridge between SAP Business Technology Platform "
        "and the AgentGovern OS distributed governance control plane. "
        "Accepts SAP CloudEvents, enforces governance policies, and returns "
        "workflow-compatible verdicts."
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

# ─── Core Adapter Logic ────────────────────────────────────────────────────────

def map_sap_event_to_action(event: SAPCloudEvent) -> dict:
    """Normalize a CloudEvent (SAP, Stripe, AWS, GitHub, Salesforce) into an AgentGovern action."""
    mapping = UNIVERSAL_EVENT_MAP.get(event.type, {
        "action_type": "unknown_event_action",
        "agent_role": "unregistered_agent",  # Triggers zero-trust BLOCK for unknown events
        "amount_field": None,
        "currency_field": None,
    })

    amount = 0.0
    if mapping["amount_field"] and mapping["amount_field"] in event.data:
        try:
            amount = float(event.data[mapping["amount_field"]])
        except (ValueError, TypeError):
            amount = 0.0

    currency = "INR"
    if mapping["currency_field"] and mapping["currency_field"] in event.data:
        currency = event.data.get(mapping["currency_field"], "INR")

    return {
        "action_type": mapping["action_type"],
        "agent_role": mapping["agent_role"],
        "role": mapping["agent_role"],  # alias for backwards compat with caller code
        "amount": amount,
        "currency": currency,
        "sap_event_id": event.id,
        "sap_source": event.source,
        "sap_event_type": event.type,
        "sap_source_system": event.sap_source_system or "unknown",
        "sap_payload": event.data,
    }


def verdict_to_sap_workflow(verdict_str: str, reasoning: str) -> dict:
    """Convert AgentGovern verdict to SAP workflow decision format."""
    verdict_upper = verdict_str.upper

    if verdict_upper == "APPROVE":
        return {
            "workflow_decision": "APPROVE",
            "requires_human_review": False,
            "escalation_contact": None,
        }
    elif verdict_upper == "BLOCK":
        return {
            "workflow_decision": "REJECT",
            "requires_human_review": True,
            "escalation_contact": "compliance@enterprise.com",
        }
    else:  # ESCALATE
        return {
            "workflow_decision": "DELEGATE",
            "requires_human_review": True,
            "escalation_contact": "governance-desk@enterprise.com",
        }


async def find_or_create_agent_for_role(role: str, client: httpx.AsyncClient) -> str | None:
    """Find an agent matching the required role in the governance registry."""
    try:
        resp = await client.get(
            f"{GOVERNANCE_API_URL}/api/v1/agents/",
            params={"role": role, "status_filter": "active", "limit": 1},
            timeout=5.0,
        )
        if resp.status_code == 200:
            data = resp.json
            agents = data.get("agents", [])
            if agents:
                return agents[0]["id"]
    except httpx.RequestError as e:
        logger.warning(f"[SAP-ADAPTER] Could not reach Governance API: {e}")
    return None


# ─── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root():
    return {
        "name": "AgentGovern OS — SAP BTP Adapter",
        "version": "1.0.0",
        "status": "operational",
        "governance_api": GOVERNANCE_API_URL,
        "supported_event_types": list(SAP_EVENT_MAP.keys()),
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Check adapter health and connectivity to the Governance API."""
    governance_status = "unreachable"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GOVERNANCE_API_URL}/health", timeout=3.0)
            if resp.status_code == 200:
                governance_status = "connected"
    except Exception:
        pass

    return {
        "status": "ok",
        "adapter_version": "1.0.0",
        "governance_api": governance_status,
        "supported_events": len(SAP_EVENT_MAP),
    }


@app.post(
    "/sap/governance/evaluate",
    response_model=SAPGovernanceVerdictResponse,
    tags=["governance"],
    summary="Evaluate a SAP BTP event through AgentGovern OS",
    description=(
        "Accepts a SAP BTP CloudEvent, maps it to an agent action, "
        "evaluates it against the active governance policies, and returns "
        "an SAP-compatible workflow decision."
    ),
)
async def evaluate_sap_event(event: SAPCloudEvent) -> SAPGovernanceVerdictResponse:
    """Main entrypoint: SAP event → AgentGovern OS → Governance verdict."""
    timestamp = datetime.now(UTC).isoformat()

    async with httpx.AsyncClient() as client:
        # 1. Normalize SAP event into AgentGovern action
        action = map_sap_event_to_action(event)

        # 2. Find matching governed agent
        agent_id = await find_or_create_agent_for_role(action["role"], client)
        if not agent_id:
            # Fallback: return deny for unknown agents (zero-trust default)
            logger.warning(f"[SAP-ADAPTER] No agent found for role '{action['role']}' — denying by default")
            return SAPGovernanceVerdictResponse(
                event_id=event.id,
                sap_source=event.source,
                sap_event_type=event.type,
                agent_assigned="UNREGISTERED",
                verdict="BLOCK",
                confidence=0.99,
                reasoning="Zero-trust default: No registered agent found for this SAP event type.",
                policy_violations=["UNREGISTERED_AGENT"],
                audit_hash=None,
                governance_timestamp=timestamp,
                workflow_decision="REJECT",
                requires_human_review=True,
                escalation_contact="governance-desk@enterprise.com",
            )

        # 3. Call SENTINEL policy evaluation
        sentinel_payload = {
            "agent_id": agent_id,
            "action": {
                "action_type": action["action_type"],
                "amount": action["amount"],
                "currency": action.get("currency", "INR"),
                "sap_source": event.source,
            },
            "context": {
                "environment": "Cloud (SAP BTP)",
                "sap_event_type": event.type,
                "sap_source_system": action.get("sap_source_system"),
                "sap_event_id": event.id,
            },
        }

        verdict_data = {
            "verdict": "escalate",
            "reasoning": "Governance API unreachable — defaulting to ESCALATE (safe mode)",
            "policy_results": [],
            "confidence": 0.5,
        }

        try:
            sentinel_resp = await client.post(
                f"{GOVERNANCE_API_URL}/api/v1/sentinel/evaluate",
                json=sentinel_payload,
                timeout=10.0,
            )
            if sentinel_resp.status_code == 200:
                verdict_data = sentinel_resp.json
        except httpx.RequestError as e:
            logger.error(f"[SAP-ADAPTER] SENTINEL unreachable: {e}")

        # 4. Map verdict to SAP workflow format
        verdict_str = verdict_data.get("verdict", "escalate")
        workflow = verdict_to_sap_workflow(verdict_str, verdict_data.get("reasoning", ""))

        # 5. Extract policy violations for SAP response
        policy_violations = [
            r["policy_code"]
            for r in verdict_data.get("policy_results", [])
            if not r.get("passed", True)
        ]

        return SAPGovernanceVerdictResponse(
            event_id=event.id,
            sap_source=event.source,
            sap_event_type=event.type,
            agent_assigned=agent_id,
            verdict=verdict_str.upper,
            confidence=verdict_data.get("confidence", 0.0),
            reasoning=verdict_data.get("reasoning", ""),
            policy_violations=policy_violations,
            audit_hash=None,  # Set if/when Decision Ledger is written
            governance_timestamp=timestamp,
            **workflow,
        )


@app.post(
    "/sap/governance/batch",
    response_model=list[SAPGovernanceVerdictResponse],
    tags=["governance"],
    summary="Batch evaluate multiple SAP events",
)
async def batch_evaluate_sap_events(batch: BatchSAPEventRequest) -> list[SAPGovernanceVerdictResponse]:
    """Process multiple SAP events in sequence."""
    results = []
    for event in batch.events:
        result = await evaluate_sap_event(event)
        results.append(result)
    return results


@app.get(
    "/sap/events/supported",
    tags=["metadata"],
    summary="List all supported SAP event types",
)
async def list_supported_events():
    """Returns the full list of SAP event types this adapter can handle."""
    return {
        "count": len(SAP_EVENT_MAP),
        "events": [
            {
                "type": event_type,
                "action_type": mapping["action_type"],
                "agent_role": mapping["agent_role"],
                "has_amount": mapping["amount_field"] is not None,
            }
            for event_type, mapping in SAP_EVENT_MAP.items()
        ],
    }


@app.post(
    "/sap/webhook/btp",
    tags=["webhooks"],
    summary="SAP BTP Webhook receiver (CloudEvents format)",
)
async def receive_btp_webhook(
    request: Request,
    ce_specversion: str | None = Header(None, alias="ce-specversion"),
    ce_type: str | None = Header(None, alias="ce-type"),
    ce_source: str | None = Header(None, alias="ce-source"),
    ce_id: str | None = Header(None, alias="ce-id"),
):
    """
    Receive SAP BTP events delivered via HTTP CloudEvents webhook (binary content mode).
    Extracts CloudEvent headers and routes to governance evaluation.
    """
    body = await request.json

    event = SAPCloudEvent(
        specversion=ce_specversion or "1.0",
        id=ce_id or str(uuid.uuid4),
        source=ce_source or "/sap/btp/unknown",
        type=ce_type or "com.sap.btp.workflow.v1.WorkflowInstance.Started.v1",
        data=body,
    )

    return await evaluate_sap_event(event)


# ─── SAP OData Bridge ─────────────────────────────────────────────────────────

class ODataQueryRequest(BaseModel):
    """Governed OData V4 query request."""
    entity_set: str = Field(..., description="OData entity set, e.g. 'PurchaseOrderSet'")
    filter: str | None = Field(None, description="OData $filter expression")
    select: str | None = Field(None, description="OData $select fields")
    top: int = Field(default=20, ge=1, le=1000)
    skip: int = Field(default=0, ge=0)
    agent_role: str = Field(default="fi_analyst", description="Role of the requesting agent")
    odata_service_url: str | None = Field(
        None,
        description="Full OData service root URL. Falls back to SAP_ODATA_BASE_URL env var.",
    )


class ODataActionRequest(BaseModel):
    """Governed OData action / function import call."""
    action_name: str = Field(..., description="OData action or function import name")
    parameters: dict = Field(default_factory=dict)
    agent_role: str = Field(default="fi_analyst")
    estimated_impact: float = Field(default=0.0, description="Estimated financial impact (INR)")


@app.post(
    "/sap/odata/query",
    tags=["odata"],
    summary="Governed OData V4 entity query",
)
async def governed_odata_query(req: ODataQueryRequest):
    """Pass an SAP OData query through the governance pipeline before execution.

    Flow:
      1. Evaluate the data-read action via SENTINEL (data_access policy check)
      2. If APPROVE → proxy the OData call to the SAP service and return results
      3. If BLOCK / ESCALATE → return the verdict without executing the query

    This prevents unauthorised data reads by governed agents.
    """
    import os

    base_url = req.odata_service_url or os.getenv("SAP_ODATA_BASE_URL", "")

    async with httpx.AsyncClient() as client:
        # Step 1: Find agent for role
        agent_id = await find_or_create_agent_for_role(req.agent_role, client)

        # Step 2: Govern the data-read action
        sentinel_payload = {
            "agent_id": agent_id,
            "action": {
                "action_type": "query_data",
                "amount": 0,
                "target_entity": req.entity_set,
                "filter": req.filter,
            },
            "context": {
                "environment": "Cloud (SAP BTP)",
                "odata_entity": req.entity_set,
                "rows_requested": req.top,
            },
        }

        verdict_str = "escalate"
        reasoning = "Governance API unreachable"
        confidence = 0.5

        if agent_id:
            try:
                resp = await client.post(
                    f"{GOVERNANCE_API_URL}/api/v1/sentinel/evaluate",
                    json=sentinel_payload,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    vd = resp.json
                    verdict_str = vd.get("verdict", "escalate")
                    reasoning = vd.get("reasoning", "")
                    confidence = vd.get("confidence", 0.5)
            except httpx.RequestError as e:
                logger.error(f"[ODATA-BRIDGE] SENTINEL unreachable: {e}")
        else:
            verdict_str = "block"
            reasoning = "Zero-trust: no registered agent for this role"
            confidence = 0.99

        if verdict_str.upper != "APPROVE":
            return {
                "governed": True,
                "verdict": verdict_str.upper,
                "reasoning": reasoning,
                "confidence": confidence,
                "odata_result": None,
                "message": "OData query blocked by governance policy.",
            }

        # Step 3: Execute the OData query if approved
        odata_result = None
        if base_url:
            try:
                params: dict = {"$top": req.top, "$skip": req.skip}
                if req.filter:
                    params["$filter"] = req.filter
                if req.select:
                    params["$select"] = req.select
                params["$format"] = "json"

                odata_resp = await client.get(
                    f"{base_url}/{req.entity_set}",
                    params=params,
                    timeout=15.0,
                    headers={"Accept": "application/json"},
                )
                odata_result = odata_resp.json
            except Exception as e:
                odata_result = {"error": str(e), "note": "OData call failed post-governance"}
        else:
            odata_result = {
                "note": "No SAP_ODATA_BASE_URL configured — governance verdict returned only",
                "entity_set": req.entity_set,
                "filter": req.filter,
            }

        return {
            "governed": True,
            "verdict": "APPROVE",
            "reasoning": reasoning,
            "confidence": confidence,
            "odata_result": odata_result,
        }


@app.post(
    "/sap/odata/action",
    tags=["odata"],
    summary="Governed OData action / function import call",
)
async def governed_odata_action(req: ODataActionRequest):
    """Govern an SAP OData action invocation (e.g., ApproveWorkflowItem, PostDocument).

    Higher-risk than a query — uses the estimated_impact amount for policy evaluation.
    """
    async with httpx.AsyncClient() as client:
        agent_id = await find_or_create_agent_for_role(req.agent_role, client)

        sentinel_payload = {
            "agent_id": agent_id,
            "action": {
                "action_type": req.action_name.lower(),
                "amount": req.estimated_impact,
                "odata_action": req.action_name,
                "parameters": req.parameters,
            },
            "context": {
                "environment": "Cloud (SAP BTP)",
                "odata_action": req.action_name,
                "estimated_impact": req.estimated_impact,
            },
        }

        verdict_data: dict = {
            "verdict": "escalate",
            "reasoning": "Governance API unreachable",
            "confidence": 0.5,
            "policy_results": [],
        }

        if agent_id:
            try:
                resp = await client.post(
                    f"{GOVERNANCE_API_URL}/api/v1/sentinel/evaluate",
                    json=sentinel_payload,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    verdict_data = resp.json
            except httpx.RequestError:
                pass

        workflow = verdict_to_sap_workflow(
            verdict_data.get("verdict", "escalate"),
            verdict_data.get("reasoning", ""),
        )

        return {
            "governed": True,
            "action_name": req.action_name,
            "verdict": verdict_data.get("verdict", "escalate").upper,
            "reasoning": verdict_data.get("reasoning", ""),
            "confidence": verdict_data.get("confidence", 0.5),
            "workflow_decision": workflow["workflow_decision"],
            "requires_human_review": workflow["requires_human_review"],
            "policy_violations": [
                r["policy_code"]
                for r in verdict_data.get("policy_results", [])
                if not r.get("passed", True)
            ],
            "governance_timestamp": datetime.now(UTC).isoformat,
        }


# ─── SAP Joule Integration ────────────────────────────────────────────────────

class JouleQueryRequest(BaseModel):
    """SAP Joule (AI copilot) governed query request."""
    user_query: str = Field(..., description="Natural language query from the Joule user")
    user_id: str = Field(..., description="SAP user ID or email of the Joule session owner")
    joule_session_id: str = Field(default_factory=lambda: str(uuid.uuid4))
    context_system: str = Field(
        default="S4HANA",
        description="Source SAP system context: S4HANA | Ariba | SuccessFactors | BTP",
    )
    data_sensitivity: str = Field(
        default="internal",
        description="Data sensitivity level: public | internal | confidential | restricted",
    )
    estimated_data_rows: int = Field(default=0, description="Estimated rows the query would touch")


@app.post(
    "/sap/joule/query",
    tags=["joule"],
    summary="Govern a SAP Joule AI copilot query",
)
async def govern_joule_query(req: JouleQueryRequest):
    """Intercept and govern a SAP Joule AI query before it accesses enterprise data.

    Joule queries are evaluated against:
      - Data access policies (sensitivity classification)
      - User entitlements (mapped to agent trust tier)
      - Volume thresholds (large data extracts require escalation)

    A governed Joule response instructs whether Joule should:
      - Proceed and answer the query (APPROVE)
      - Refuse with a policy explanation (BLOCK)
      - Route to a human reviewer (ESCALATE)
    """

    # Detect high-risk query patterns
    risk_keywords = [
        "salary", "payroll", "ssn", "social security", "password", "secret",
        "export all", "download all", "bulk", "delete", "drop table",
        "bank account", "iban", "card number",
    ]
    query_lower = req.user_query.lower
    detected_risks = [kw for kw in risk_keywords if kw in query_lower]

    # Map Joule query to an action type
    if any(w in query_lower for w in ["delete", "remove", "drop"]):
        action_type = "delete_data"
        base_impact = 50000.0
    elif any(w in query_lower for w in ["export", "download", "extract", "all records"]):
        action_type = "export_sensitive_data"
        base_impact = float(req.estimated_data_rows * 10)
    elif any(w in query_lower for w in ["update", "change", "modify", "set"]):
        action_type = "modify_data"
        base_impact = 5000.0
    else:
        action_type = "query_data"
        base_impact = 0.0

    sensitivity_multiplier = {
        "public": 1.0,
        "internal": 2.0,
        "confidential": 5.0,
        "restricted": 10.0,
    }.get(req.data_sensitivity, 2.0)

    impact = base_impact * sensitivity_multiplier
    if detected_risks:
        impact = max(impact, 100000.0)  # Force escalation threshold for PII-related queries

    # Map user to agent role
    joule_agent_role = "joule_fi_analyst" if req.context_system in ("S4HANA", "Ariba") else "joule_agent"

    async with httpx.AsyncClient() as client:
        agent_id = await find_or_create_agent_for_role(joule_agent_role, client)
        if not agent_id:
            agent_id = await find_or_create_agent_for_role("fi_analyst", client)

        sentinel_payload = {
            "agent_id": agent_id,
            "action": {
                "action_type": action_type,
                "amount": impact,
                "user_query": req.user_query[:200],
                "data_sensitivity": req.data_sensitivity,
                "detected_risk_keywords": detected_risks,
            },
            "context": {
                "environment": f"Cloud (SAP {req.context_system})",
                "source": "joule_copilot",
                "joule_session_id": req.joule_session_id,
                "user_id": req.user_id,
                "estimated_data_rows": req.estimated_data_rows,
            },
        }

        verdict_data: dict = {
            "verdict": "escalate",
            "reasoning": "Governance API unreachable — Joule query blocked (safe mode)",
            "confidence": 0.5,
            "policy_results": [],
        }

        if agent_id:
            try:
                resp = await client.post(
                    f"{GOVERNANCE_API_URL}/api/v1/sentinel/evaluate",
                    json=sentinel_payload,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    verdict_data = resp.json
            except httpx.RequestError as e:
                logger.error(f"[JOULE] SENTINEL unreachable: {e}")

    verdict = verdict_data.get("verdict", "escalate").upper

    joule_response_hint = {
        "APPROVE": "Proceed with answering the user query.",
        "BLOCK": (
            "Do not answer this query. Respond: "
            "'I'm unable to assist with this request due to enterprise data governance policies.'"
        ),
        "ESCALATE": (
            "Pause and inform the user: "
            "'This query requires additional authorisation. "
            "A governance review has been initiated and you will be notified.'"
        ),
    }.get(verdict, "Pause and await governance review.")

    return {
        "governed": True,
        "joule_session_id": req.joule_session_id,
        "user_id": req.user_id,
        "verdict": verdict,
        "joule_instruction": joule_response_hint,
        "reasoning": verdict_data.get("reasoning", ""),
        "confidence": verdict_data.get("confidence", 0.5),
        "detected_risks": detected_risks,
        "action_type": action_type,
        "estimated_impact": impact,
        "policy_violations": [
            r["policy_code"]
            for r in verdict_data.get("policy_results", [])
            if not r.get("passed", True)
        ],
        "requires_human_review": verdict != "APPROVE",
        "governance_timestamp": datetime.now(UTC).isoformat,
    }


# ─── S/4HANA Workflow Trigger for ECLIPSE Escalations ────────────────────────

class S4HANAWorkflowTriggerRequest(BaseModel):
    """Trigger an SAP S/4HANA or BTP workflow for a governance escalation."""
    escalation_case_id: str = Field(..., description="AgentGovern OS EscalationCase ID")
    agent_code: str = Field(..., description="Agent code involved in the escalation")
    escalation_reason: str = Field(..., description="Reason for escalation")
    action_context: dict = Field(default_factory=dict, description="Original action context")
    priority: str = Field(default="medium", description="high | medium | low")
    # SAP BTP Workflow configuration (optional — uses env vars as fallback)
    btp_workflow_definition_id: str = Field(
        default="agentgovern-escalation-review",
        description="SAP BTP Workflow Definition ID",
    )
    s4hana_workflow_task: str | None = Field(
        None,
        description="Optional: SAP S/4HANA work item task code for direct inbox creation",
    )


class S4HANAWorkflowResponse(BaseModel):
    triggered: bool
    workflow_instance_id: str | None
    workflow_type: str
    escalation_case_id: str
    sap_inbox_url: str | None
    message: str
    triggered_at: str


@app.post(
    "/sap/s4hana/workflow/trigger",
    response_model=S4HANAWorkflowResponse,
    tags=["s4hana"],
    summary="Trigger SAP S/4HANA / BTP workflow for a governance escalation",
)
async def trigger_s4hana_workflow(req: S4HANAWorkflowTriggerRequest):
    """When ECLIPSE creates a governance escalation, fire an SAP BTP Workflow instance
    so the human reviewer gets a task in their SAP Inbox (My Inbox / Fiori Launchpad).

    Integration path:
      AgentGovern ECLIPSE → POST /sap/s4hana/workflow/trigger
        → SAP BTP Workflow Service REST API
          → My Inbox task for the designated approver
            → Approver decision synced back via /sap/webhook/btp

    If SAP_BTP_WORKFLOW_URL is not configured, the adapter returns a simulated
    workflow response (sandbox mode) so the rest of the flow can be tested.
    """
    import os

    btp_workflow_url = os.getenv("SAP_BTP_WORKFLOW_URL", "")
    btp_auth_token = os.getenv("SAP_BTP_AUTH_TOKEN", "")

    workflow_instance_id = None
    triggered = False
    workflow_type = "simulation"
    sap_inbox_url = None
    message = ""

    priority_map = {"high": "VERY_HIGH", "medium": "MEDIUM", "low": "LOW"}
    sap_priority = priority_map.get(req.priority, "MEDIUM")

    context_payload = {
        "escalationCaseId": req.escalation_case_id,
        "agentCode": req.agent_code,
        "escalationReason": req.escalation_reason,
        "priority": sap_priority,
        "actionContext": req.action_context,
        "governanceApiUrl": GOVERNANCE_API_URL,
        "resolveCallbackUrl": f"{GOVERNANCE_API_URL}/api/v1/escalations/{req.escalation_case_id}/resolve",
        "createdAt": datetime.now(UTC).isoformat,
    }

    if btp_workflow_url and btp_auth_token:
        try:
            async with httpx.AsyncClient() as client:
                wf_resp = await client.post(
                    f"{btp_workflow_url}/v1/workflow-instances",
                    json={
                        "definitionId": req.btp_workflow_definition_id,
                        "context": context_payload,
                    },
                    headers={
                        "Authorization": f"Bearer {btp_auth_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=15.0,
                )
                if wf_resp.status_code in (200, 201):
                    wf_data = wf_resp.json
                    workflow_instance_id = wf_data.get("id", str(uuid.uuid4))
                    triggered = True
                    workflow_type = "sap_btp_workflow"
                    sap_inbox_url = (
                        f"{btp_workflow_url.replace('/workflow-service/rest', '')}"
                        f"/launchpad#WorkflowTask-displayMyInbox"
                    )
                    message = f"SAP BTP Workflow instance {workflow_instance_id} created."
                else:
                    message = f"BTP Workflow API returned {wf_resp.status_code}: {wf_resp.text[:200]}"
        except Exception as e:
            message = f"Failed to reach SAP BTP Workflow Service: {e}"
    else:
        # Simulation mode — generate a fake workflow instance
        workflow_instance_id = f"WF-SIM-{uuid.uuid4.hex[:8].upper}"
        triggered = True
        workflow_type = "simulation"
        sap_inbox_url = None
        message = (
            f"[SIMULATION] SAP BTP Workflow not configured "
            f"(set SAP_BTP_WORKFLOW_URL + SAP_BTP_AUTH_TOKEN). "
            f"Simulated instance: {workflow_instance_id}"
        )

    logger.info(
        f"[S4WORKFLOW] Escalation {req.escalation_case_id}: "
        f"triggered={triggered} type={workflow_type} instance={workflow_instance_id}"
    )

    return S4HANAWorkflowResponse(
        triggered=triggered,
        workflow_instance_id=workflow_instance_id,
        workflow_type=workflow_type,
        escalation_case_id=req.escalation_case_id,
        sap_inbox_url=sap_inbox_url,
        message=message,
        triggered_at=datetime.now(UTC).isoformat,
    )
