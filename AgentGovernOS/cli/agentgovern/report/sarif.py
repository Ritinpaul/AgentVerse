"""
SARIF Output Generator — produces SARIF 2.1.0 format for CI/CD integration.

SARIF is supported natively by GitHub Code Scanning (upload-sarif action),
Azure DevOps, VS Code, and many other tools.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from agentgovern import __version__

if TYPE_CHECKING:
    from agentgovern.policy.engine import PolicyCheckResult
    from agentgovern.scanner.codeprint import CodeprintScanResult

SEVERITY_LEVEL_MAP = {
    "CRITICAL": "error",
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "note",
}


def build_sarif(
    policy_result: "PolicyCheckResult",
    codeprint_result: "CodeprintScanResult",
) -> dict[str, Any]:
    """Build a SARIF 2.1.0 document from policy check results."""

    rules: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    seen_rule_ids: set[str] = set

    # ── Policy violations ──────────────────────────────────────────────────
    for v in policy_result.violations:
        if v.rule_id not in seen_rule_ids:
            seen_rule_ids.add(v.rule_id)
            rules.append({
                "id": v.rule_id,
                "name": v.rule_name.replace(" ", ""),
                "shortDescription": {"text": v.rule_name},
                "fullDescription": {"text": v.message},
                "helpUri": f"https://github.com/Ritinpaul/AgentGovern-OS/blob/main/cli/README.md#{v.rule_id.lower}",
                "defaultConfiguration": {
                    "level": SEVERITY_LEVEL_MAP.get(v.severity, "warning")
                },
            })

        location: dict[str, Any] = {}
        if v.source_file:
            location = {
                "physicalLocation": {
                    "artifactLocation": {"uri": v.source_file, "uriBaseId": "%SRCROOT%"},
                }
            }
        else:
            location = {
                "physicalLocation": {
                    "artifactLocation": {"uri": "agentgovern.yaml", "uriBaseId": "%SRCROOT%"}
                }
            }

        results.append({
            "ruleId": v.rule_id,
            "level": SEVERITY_LEVEL_MAP.get(v.severity, "warning"),
            "message": {
                "text": f"{v.message}\n\nSuggestion: {v.suggestion}"
            },
            "locations": [location],
        })

    # ── Secret detections ─────────────────────────────────────────────────
    secret_rule_id = "AG-SEC-HARDCODED"
    if codeprint_result.secret_detections and secret_rule_id not in seen_rule_ids:
        rules.append({
            "id": secret_rule_id,
            "name": "HardcodedSecret",
            "shortDescription": {"text": "Hardcoded API key or secret detected"},
            "fullDescription": {"text": "Hardcoded credentials were found in source code."},
            "defaultConfiguration": {"level": "error"},
        })

    for s in codeprint_result.secret_detections:
        results.append({
            "ruleId": secret_rule_id,
            "level": "error",
            "message": {"text": f"Hardcoded {s.secret_type} detected: {s.snippet}"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": s.file, "uriBaseId": "%SRCROOT%"},
                    "region": {"startLine": s.line},
                }
            }],
        })

    # ── Assemble SARIF document ────────────────────────────────────────────
    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "AgentGovern",
                    "version": __version__,
                    "informationUri": "https://github.com/Ritinpaul/AgentGovern-OS",
                    "rules": rules,
                }
            },
            "results": results,
        }],
    }


def save_sarif(sarif: dict[str, Any], output_path: Path) -> None:
    """Write the SARIF document to a file."""
    output_path.write_text(json.dumps(sarif, indent=2), encoding="utf-8")
