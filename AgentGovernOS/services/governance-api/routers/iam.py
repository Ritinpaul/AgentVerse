"""
AgentGovernOS — IAM & STS Router
================──────────────────
AWS IAM-style Identity & Security Token Service (STS) for AgentVerse.
Provides ARN parsing, AssumeRole temporary session credentials, and JSON Policy evaluation.
Fully non-breaking and 100% backwards compatible with existing RBAC tokens.
"""

import re
import time
from typing import Any

from fastapi import APIRouter, Header
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from services.auth import ALGORITHM, AuthService

router = APIRouter(prefix="/iam", tags=["iam"])

# ── ARN Parsing Utility ───────────────────────────────────────────────────────
# ARN Format: arn:agentverse:<pillar>:<region>:<org_id>:<resource_type>/<resource_id>
ARN_REGEX = re.compile(
    r"^arn:agentverse:(?P<pillar>[a-z0-9_-]+):(?P<region>[a-z0-9_-]*):(?P<org_id>[a-z0-9_-]+):(?P<resource_type>[a-z0-9_-]+)/(?P<resource_id>.+)$"
)

def parse_arn(arn_str: str) -> dict[str, str]:
    match = ARN_REGEX.match(arn_str)
    if not match:
        raise ValueError(f"Invalid AgentVerse ARN format: {arn_str}")
    return match.groupdict()

def format_arn(pillar: str, region: str, org_id: str, resource_type: str, resource_id: str) -> str:
    return f"arn:agentverse:{pillar}:{region}:{org_id}:{resource_type}/{resource_id}"


# ── Built-in IAM Role Definitions ─────────────────────────────────────────────
DEFAULT_IAM_ROLES: dict[str, dict[str, Any]] = {
    "OwnerRole": {
        "role_arn": "arn:agentverse:iam::org_default:role/OwnerRole",
        "name": "Organization Owner",
        "description": "Full Root Super-Admin access to Billing, Org Deletion, Key Rotation, & Policies",
        "badge_color": "bg-[#EC4899]/15 border-[#EC4899]/40 text-[#F472B6]",
        "statements": [
            {
                "Sid": "AllowAllActions",
                "Effect": "Allow",
                "Action": ["*"],
                "Resource": ["*"]
            }
        ]
    },
    "AdminRole": {
        "role_arn": "arn:agentverse:iam::org_default:role/AdminRole",
        "name": "System Administrator",
        "description": "Manage Team Members, MicroVM Infrastructure, and GovernOS Safety Policies",
        "badge_color": "bg-[#8B5CF6]/15 border-[#8B5CF6]/40 text-[#C084FC]",
        "statements": [
            {
                "Sid": "AllowAdminOperations",
                "Effect": "Allow",
                "Action": [
                    "iam:ManageTeam",
                    "governos:EditPolicies",
                    "agentos:DeployMicroVM",
                    "agentos:ExecuteAgent",
                    "agentstore:PublishAgent",
                    "audit:ViewLogs"
                ],
                "Resource": ["*"]
            },
            {
                "Sid": "DenyBillingAndOrgDelete",
                "Effect": "Deny",
                "Action": [
                    "billing:ManageSubscription",
                    "iam:DeleteOrganization",
                    "iam:TransferOwnership"
                ],
                "Resource": ["*"]
            }
        ]
    },
    "DeveloperRole": {
        "role_arn": "arn:agentverse:iam::org_default:role/DeveloperRole",
        "name": "Agent Developer (Write)",
        "description": "Develop agents, edit prompts, test locally, and deploy to Staging MicroVMs",
        "badge_color": "bg-[#10B981]/15 border-[#10B981]/40 text-[#34D399]",
        "statements": [
            {
                "Sid": "AllowDeveloperActions",
                "Effect": "Allow",
                "Action": [
                    "agentstudio:EditPrompt",
                    "agentos:RunLocally",
                    "agentos:DeployStaging",
                    "agentos:ExecuteAgent",
                    "audit:ViewLogs"
                ],
                "Resource": ["*"]
            },
            {
                "Sid": "DenyAdminAndPolicies",
                "Effect": "Deny",
                "Action": [
                    "governos:EditPolicies",
                    "iam:ManageTeam",
                    "billing:ManageSubscription"
                ],
                "Resource": ["*"]
            }
        ]
    },
    "AuditorRole": {
        "role_arn": "arn:agentverse:iam::org_default:role/AuditorRole",
        "name": "Compliance Auditor (Read)",
        "description": "Read-only access to audit ledgers, telemetry traces, and compliance reports",
        "badge_color": "bg-[#3B82F6]/15 border-[#3B82F6]/30 text-[#60A5FA]",
        "statements": [
            {
                "Sid": "AllowReadLogsAndAudit",
                "Effect": "Allow",
                "Action": [
                    "audit:ViewLogs",
                    "governos:ViewPolicies",
                    "telemetry:ViewTraces"
                ],
                "Resource": ["*"]
            },
            {
                "Sid": "DenyAllMutations",
                "Effect": "Deny",
                "Action": [
                    "agentos:ExecuteAgent",
                    "agentos:DeployMicroVM",
                    "agentstudio:EditPrompt",
                    "governos:EditPolicies"
                ],
                "Resource": ["*"]
            }
        ]
    }
}


# ── Request / Response Schemas ────────────────────────────────────────────────
class AssumeRoleRequest(BaseModel):
    role_arn: str = Field(..., example="arn:agentverse:iam::org_default:role/AdminRole")
    session_name: str = Field(default="ConsoleUserSession")
    duration_seconds: int = Field(default=3600, ge=900, le=43200)

class AssumeRoleResponse(BaseModel):
    assumed_role_arn: str
    session_token: str
    expires_in: int
    user_arn: str
    role_name: str
    badge_color: str
    permissions: list[str]

class PolicyEvaluateRequest(BaseModel):
    action: str = Field(..., example="agentos:DeployMicroVM")
    resource_arn: str = Field(..., example="arn:agentverse:agentos:us-east-1:org_default:agent/trading-bot")
    role_arn: str | None = None

class PolicyEvaluateResponse(BaseModel):
    allowed: bool
    reason: str
    matched_statement: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_iam_roles() -> dict[str, Any]:
    """List available IAM Roles for the organization."""
    return {"roles": list(DEFAULT_IAM_ROLES.values())}


@router.post("/sts/assume-role", response_model=AssumeRoleResponse)
async def assume_role(
    body: AssumeRoleRequest,
    authorization: str | None = Header(None)
) -> AssumeRoleResponse:
    """
    AWS STS-style AssumeRole endpoint.
    Issues a short-lived temporary session JWT with assumed role permissions.
    """
    user_email = "developer@nuuvixx.ai"
    user_id = "demo-user-id"
    org_id = "org_default"

    # Decode authorization header if provided
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization.split(" ")[1]
        try:
            secret = AuthService.get_secret_key()
            payload = jwt.decode(token_str, secret, algorithms=[ALGORITHM], options={"verify_exp": False})
            user_email = payload.get("email", user_email)
            user_id = payload.get("sub", user_id)
            org_id = payload.get("org_id", org_id)
        except JWTError:
            pass

    # Resolve target role definition
    target_role_name = body.role_arn.split("/")[-1] if "/" in body.role_arn else body.role_arn
    role_def = DEFAULT_IAM_ROLES.get(target_role_name)

    if not role_def:
        # Fallback dynamic role creation if custom role requested
        role_def = {
            "role_arn": body.role_arn,
            "name": target_role_name,
            "description": "Custom Assumed IAM Role Session",
            "badge_color": "bg-[#8B5CF6]/15 border-[#8B5CF6]/40 text-[#C084FC]",
            "statements": [
                {
                    "Sid": "AllowCustomSession",
                    "Effect": "Allow",
                    "Action": ["*"],
                    "Resource": ["*"]
                }
            ]
        }

    now = int(time.time())
    expires_in = body.duration_seconds

    user_arn = f"arn:agentverse:iam::{org_id}:user/{user_email.split('@')[0]}"
    session_arn = f"{role_def['role_arn']}/{body.session_name}"

    # Extract allowed actions for token claims
    actions: list[str] = []
    for stmt in role_def.get("statements", []):
        if stmt.get("Effect") == "Allow":
            actions.extend(stmt.get("Action", []))

    # Map target role to legacy role string for 100% backwards compatibility
    legacy_role_map = {
        "OwnerRole": "owner",
        "AdminRole": "admin",
        "DeveloperRole": "developer",
        "AuditorRole": "auditor"
    }
    legacy_role = legacy_role_map.get(target_role_name, "developer")

    secret = AuthService.get_secret_key()
    session_payload = {
        "sub": user_id,
        "email": user_email,
        "org_id": org_id,
        "user_arn": user_arn,
        "assumed_role_arn": role_def["role_arn"],
        "session_arn": session_arn,
        "roles": [legacy_role],
        "iam_actions": actions,
        "iat": now,
        "exp": now + expires_in,
    }

    session_token = jwt.encode(session_payload, secret, algorithm=ALGORITHM)

    return AssumeRoleResponse(
        assumed_role_arn=role_def["role_arn"],
        session_token=session_token,
        expires_in=expires_in,
        user_arn=user_arn,
        role_name=role_def["name"],
        badge_color=role_def["badge_color"],
        permissions=actions
    )


@router.post("/policies/evaluate", response_model=PolicyEvaluateResponse)
async def evaluate_policy(body: PolicyEvaluateRequest) -> PolicyEvaluateResponse:
    """
    Evaluates whether an action on a target resource ARN is allowed under an IAM Role.
    Deny statements strictly override Allow statements (AWS IAM Standard).
    """
    role_name = "AdminRole"
    if body.role_arn:
        role_name = body.role_arn.split("/")[-1]

    role_def = DEFAULT_IAM_ROLES.get(role_name, DEFAULT_IAM_ROLES["AdminRole"])
    statements = role_def.get("statements", [])

    # 1. Explicit Deny Check
    for stmt in statements:
        if stmt.get("Effect") == "Deny":
            actions = stmt.get("Action", [])
            if "*" in actions or body.action in actions or any(body.action.startswith(a.replace("*", "")) for a in actions if "*" in a):
                return PolicyEvaluateResponse(
                    allowed=False,
                    reason=f"Explicit Deny statement '{stmt.get('Sid')}' blocks action {body.action}",
                    matched_statement=stmt.get("Sid")
                )

    # 2. Explicit Allow Check
    for stmt in statements:
        if stmt.get("Effect") == "Allow":
            actions = stmt.get("Action", [])
            if "*" in actions or body.action in actions or any(body.action.startswith(a.replace("*", "")) for a in actions if "*" in a):
                return PolicyEvaluateResponse(
                    allowed=True,
                    reason=f"Action {body.action} allowed by statement '{stmt.get('Sid')}'",
                    matched_statement=stmt.get("Sid")
                )

    # Default Deny if no explicit allow statement matches
    return PolicyEvaluateResponse(
        allowed=False,
        reason=f"Implicit Deny: No statement explicitly allows {body.action}",
        matched_statement=None
    )
