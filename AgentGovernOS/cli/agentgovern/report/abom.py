"""
ABOM Generator — produces the Agent Bill of Materials (ABOM) JSON document.

The ABOM is the machine-readable output of a full scan. It summarises all
detected agents, their configuration, policy violations, and risk scores.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from agentgovern import __version__

if TYPE_CHECKING:
    from agentgovern.scanner.manifest import AgentDefinition, ManifestParseResult
    from agentgovern.scanner.dependency import DependencyScanResult
    from agentgovern.scanner.codeprint import CodeprintScanResult
    from agentgovern.scanner.authority import AuthorityAnalysisResult
    from agentgovern.policy.engine import PolicyCheckResult


def build_abom(
    project: str,
    manifest_results: list["ManifestParseResult"],
    dependency_result: "DependencyScanResult",
    codeprint_result: "CodeprintScanResult",
    authority_result: "AuthorityAnalysisResult",
    policy_result: "PolicyCheckResult",
    scan_duration_s: float = 0.0,
) -> dict[str, Any]:
    """
    Build a complete ABOM (Agent Bill of Materials) document from scan results.
    """
    now = datetime.now(timezone.utc).isoformat

    # ── Collect all agents from manifests ─────────────────────────────────
    agents_section = []
    all_agents: list["AgentDefinition"] = []
    for mr in manifest_results:
        all_agents.extend(mr.agents)

    # Map agent_code → violations
    violations_by_agent: dict[str, list[dict[str, Any]]] = {}
    for v in policy_result.violations:
        code = v.agent_code or "__project__"
        violations_by_agent.setdefault(code, []).append({
            "rule_id": v.rule_id,
            "rule_name": v.rule_name,
            "severity": v.severity,
            "message": v.message,
            "suggestion": v.suggestion,
        })

    for agent in all_agents:
        risk = authority_result.risk_scores.get(agent.code, "LOW")
        agents_section.append({
            "code": agent.code,
            "name": agent.name,
            "framework": agent.framework,
            "tier": agent.tier,
            "authority_limit": agent.authority_limit,
            "currency": agent.currency,
            "allowed_actions": agent.allowed_actions,
            "denied_actions": agent.denied_actions,
            "platform_bindings": agent.platform_bindings,
            "risk_tolerance": agent.risk_tolerance,
            "risk_score": risk,
            "source_file": agent.source_file,
            "policy_violations": violations_by_agent.get(agent.code, []),
        })

    # ── Summary counts ─────────────────────────────────────────────────────
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for v in policy_result.violations:
        sev_counts[v.severity] = sev_counts.get(v.severity, 0) + 1

    # ── Detected frameworks from dependency and codeprint ──────────────────
    frameworks_detected = list(dependency_result.frameworks)
    codeprint_frameworks = list({d.framework for d in codeprint_result.agent_detections})
    all_frameworks = sorted(set(frameworks_detected + codeprint_frameworks))

    # ── Build final document ───────────────────────────────────────────────
    abom: dict[str, Any] = {
        "abom_version": "1.0",
        "schema": "https://agentgovernog.io/schema/abom/v1",
        "generated_at": now,
        "scanner_version": __version__,
        "project": project,
        "scan_metadata": {
            "policy_bundle": policy_result.bundle_name,
            "rules_checked": policy_result.rules_checked,
            "scan_duration_seconds": round(scan_duration_s, 3),
            "manifests_found": len(manifest_results),
            "source_files_scanned": codeprint_result.scanned_files,
            "dependency_files_scanned": len(dependency_result.scanned_files),
        },
        "frameworks_detected": all_frameworks,
        "agents": agents_section,
        "hardcoded_secrets": [
            {
                "secret_type": s.secret_type,
                "file": s.file,
                "line": s.line,
                "snippet": s.snippet,
            }
            for s in codeprint_result.secret_detections
        ],
        "project_violations": violations_by_agent.get("__project__", []),
        "summary": {
            "total_agents": len(agents_section),
            "total_violations": len(policy_result.violations),
            "critical": sev_counts["CRITICAL"],
            "high": sev_counts["HIGH"],
            "medium": sev_counts["MEDIUM"],
            "low": sev_counts["LOW"],
            "hardcoded_secrets": len(codeprint_result.secret_detections),
            "overall_pass": policy_result.passed and not codeprint_result.has_hardcoded_secrets,
        },
    }

    return abom


def save_abom(abom: dict[str, Any], output_path: Path) -> None:
    """Write the ABOM as a formatted JSON file."""
    output_path.write_text(json.dumps(abom, indent=2, default=str), encoding="utf-8")
