"""OWASP Coverage Router — GET /governance/owasp-coverage.

deliverable: exposes a machine-readable OWASP ASI01–ASI10 coverage
report that can be shown to CISOs and used by the AgentStore verification
pipeline.

Endpoints:
    GET /governance/owasp-coverage          — Full coverage report
    GET /governance/owasp-coverage/{asi_id} — Single risk detail
    POST /governance/owasp-coverage/evaluate — Run live ASI07/08/09 checks
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from policy.owasp import (
    OWASP_COVERAGE,
    ASI07InterAgentPolicy,
    ASI08CascadingPolicy,
    ASI09OverreliancePolicy,
    get_coverage_score,
)
from pydantic import BaseModel, Field

router = APIRouter(prefix="/governance", tags=["OWASP Coverage"])


# ─────────────────────────────────────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────────────────────────────────────

class ASIRiskDetail(BaseModel):
    asi_id: str
    name: str
    status: str           # "covered" | "partial" | "not_covered"
    controls: list[str]
    policies: list[str]
    gap: str | None
    phase_to_fill: int | None


class OWASPCoverageReport(BaseModel):
    standard: str = "OWASP Top 10 for AI Systems 2025 (ASI01–ASI10)"
    coverage_score: float = Field(..., description="Fraction of risks fully covered (0.0–1.0)")
    covered_count: int
    partial_count: int
    not_covered_count: int
    risks: dict[str, ASIRiskDetail]


class LiveEvaluationRequest(BaseModel):
    """Request to run live OWASP policy checks against a context payload."""
    asi_checks: list[str] = Field(
        default=["ASI07", "ASI08", "ASI09"],
        description="Which ASI policies to evaluate",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context payload for policy evaluation",
    )


class LiveEvaluationResult(BaseModel):
    asi_id: str
    verdict: str
    reason: str
    details: dict[str, Any]
    remediation: str


class LiveEvaluationResponse(BaseModel):
    checks_run: int
    blocking_violations: int
    escalations: int
    results: list[LiveEvaluationResult]
    overall_verdict: str  # "PASS" | "WARN" | "ESCALATE" | "BLOCK"


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/owasp-coverage",
    response_model=OWASPCoverageReport,
    summary="OWASP ASI01–ASI10 Coverage Report",
    description=(
        "Returns the AgentGovern OS coverage status for each OWASP Top 10 for AI risk. "
        "Use this to demonstrate OWASP compliance to CISOs and auditors."
    ),
)
async def get_owasp_coverage() -> OWASPCoverageReport:
    """Return the full OWASP ASI coverage map."""
    risks = {}
    covered = partial = not_covered = 0

    for asi_id, data in OWASP_COVERAGE.items:
        risks[asi_id] = ASIRiskDetail(
            asi_id=asi_id,
            name=data["name"],
            status=data["status"],
            controls=data["controls"],
            policies=data["policies"],
            gap=data.get("gap"),
            phase_to_fill=data.get("phase_to_fill"),
        )
        if data["status"] == "covered":
            covered += 1
        elif data["status"] == "partial":
            partial += 1
        else:
            not_covered += 1

    return OWASPCoverageReport(
        coverage_score=get_coverage_score,
        covered_count=covered,
        partial_count=partial,
        not_covered_count=not_covered,
        risks=risks,
    )


@router.get(
    "/owasp-coverage/{asi_id}",
    response_model=ASIRiskDetail,
    summary="Single OWASP ASI Risk Detail",
)
async def get_asi_detail(asi_id: str) -> ASIRiskDetail:
    """Return coverage detail for a single ASI risk (e.g., ASI07)."""
    asi_id_upper = asi_id.upper
    if asi_id_upper not in OWASP_COVERAGE:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown ASI ID '{asi_id}'. Valid values: ASI01–ASI10",
        )

    data = OWASP_COVERAGE[asi_id_upper]
    return ASIRiskDetail(
        asi_id=asi_id_upper,
        name=data["name"],
        status=data["status"],
        controls=data["controls"],
        policies=data["policies"],
        gap=data.get("gap"),
        phase_to_fill=data.get("phase_to_fill"),
    )


@router.post(
    "/owasp-coverage/evaluate",
    response_model=LiveEvaluationResponse,
    summary="Live OWASP Policy Evaluation",
    description=(
        "Run live ASI07/ASI08/ASI09 policy checks against a provided context. "
        "Use during agent registration or pre-deployment to get a real-time "
        "OWASP policy verdict."
    ),
)
async def evaluate_owasp_policies(request: LiveEvaluationRequest) -> LiveEvaluationResponse:
    """Run live OWASP policy evaluation against the provided context."""

    _policy_map = {
        "ASI07": ASI07InterAgentPolicy,
        "ASI08": ASI08CascadingPolicy,
        "ASI09": ASI09OverreliancePolicy,
    }

    results: list[LiveEvaluationResult] = []
    blocking = 0
    escalations = 0

    for asi_id in request.asi_checks:
        asi_upper = asi_id.upper
        policy = _policy_map.get(asi_upper)
        if not policy:
            # Non-runnable policy (ASI01-06, ASI10 are architectural controls)
            results.append(LiveEvaluationResult(
                asi_id=asi_upper,
                verdict="SKIP",
                reason=f"{asi_upper} is an architectural control — not runtime-evaluable",
                details={},
                remediation="",
            ))
            continue

        result = policy.evaluate(request.context)
        results.append(LiveEvaluationResult(
            asi_id=result.asi_id,
            verdict=result.verdict.value,
            reason=result.reason,
            details=result.details,
            remediation=result.remediation,
        ))

        if result.is_blocking:
            blocking += 1
        if result.requires_escalation:
            escalations += 1

    # Overall verdict: worst-case wins
    if blocking > 0:
        overall = "BLOCK"
    elif escalations > 0:
        overall = "ESCALATE"
    elif any(r.verdict == "WARN" for r in results):
        overall = "WARN"
    else:
        overall = "PASS"

    return LiveEvaluationResponse(
        checks_run=len(results),
        blocking_violations=blocking,
        escalations=escalations,
        results=results,
        overall_verdict=overall,
    )
