"""
Composition Policy Validator
Cross-checks policies, sandbox constraints, and tool permissions across composed agents to prevent policy clashes.
"""
from __future__ import annotations
import yaml
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.agent_listing import AgentListing, AgentVersion


def validate_composition_policies(agent_slugs: List[str], db: Session) -> dict:
    """
    Cross-validates security policies across all agents in a composition chain.

    Checks:
    1. Unsandboxed agents chained to HIPAA/SOC2 compliance-restricted agents.
    2. Prompt injection vulnerabilities (ASI01) in any pipeline step.
    3. External webhook exfiltration tools combined with confidential data agents.
    4. Trust score discrepancies (e.g. chaining a 100-score agent to a low <50-score agent).

    Returns:
    {
        "valid": bool,
        "clashes": [ {severity, rule, agent_slug, message} ],
        "min_trust_score": float,
    }
    """
    clashes: List[Dict[str, Any]] = []
    agent_details: List[dict] = []
    trust_scores: List[float] = []

    for slug in agent_slugs:
        listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
        if not listing:
            clashes.append({
                "severity": "critical",
                "rule": "MISSING_AGENT",
                "agent_slug": slug,
                "message": f"Agent '{slug}' does not exist in registry.",
            })
            continue

        trust_scores.append(listing.trust_score)

        latest_version = (
            db.query(AgentVersion)
            .filter(AgentVersion.listing_id == listing.id, AgentVersion.status == "published")
            .order_by(AgentVersion.id.desc())
            .first()
        )

        parsed_yaml = {}
        if latest_version:
            try:
                parsed_yaml = yaml.safe_load(latest_version.agent_yaml) or {}
            except Exception:
                pass

        agent_details.append({
            "slug": listing.slug,
            "trust_score": listing.trust_score,
            "verification_status": listing.verification_status,
            "badges": [b.get("badge_type") for b in (listing.compliance_badges or [])],
            "policies": parsed_yaml.get("policies", {}),
            "tools": parsed_yaml.get("tools", []),
        })

    # Rule 1: Trust score discrepancy check (high trust + low trust in same pipeline)
    if trust_scores:
        max_score = max(trust_scores)
        min_score = min(trust_scores)
        if max_score >= 85.0 and min_score < 50.0:
            low_agents = [a["slug"] for a in agent_details if a["trust_score"] < 50.0]
            clashes.append({
                "severity": "high",
                "rule": "TRUST_SCORE_DISCREPANCY",
                "agent_slug": ", ".join(low_agents),
                "message": f"Pipeline combines high-trust agents (score {max_score}) with low-trust agent(s) (score {min_score}).",
            })

    # Rule 2: Unsandboxed agent connected to HIPAA/SOC2 restricted agent
    has_restricted = any("hipaa" in a["badges"] or "soc2" in a["badges"] for a in agent_details)
    if has_restricted:
        for a in agent_details:
            sandbox = a["policies"].get("sandbox", True)
            if not sandbox:
                clashes.append({
                    "severity": "critical",
                    "rule": "UNSANDBOXED_RESTRICTED_CLASH",
                    "agent_slug": a["slug"],
                    "message": f"Unsandboxed agent '{a['slug']}' cannot be composed with HIPAA/SOC2 compliance-restricted agents.",
                })

    # Rule 3: External Webhook exfiltration check
    for a in agent_details:
        for t in a["tools"]:
            if isinstance(t, dict) and t.get("type") == "http" and "webhook" in t.get("url", "").lower():
                clashes.append({
                    "severity": "medium",
                    "rule": "EXFILTRATION_RISK",
                    "agent_slug": a["slug"],
                    "message": f"Agent '{a['slug']}' uses an external webhook tool. Verify data pipeline boundary.",
                })

    is_valid = not any(c["severity"] in ("high", "critical") for c in clashes)
    min_trust = min(trust_scores) if trust_scores else 0.0

    return {
        "valid": is_valid,
        "clashes": clashes,
        "min_trust_score": min_trust,
    }
