"""
ASI01-ASI10 Static Security Scanner
Runs heuristic checks against an agent.yaml manifest.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List


SENSITIVE_KEYWORDS = [
    "password", "secret", "api_key", "token", "credential",
    "private_key", "access_key", "auth_token", "bearer",
]

KNOWN_SAFE_MCP_SERVERS = {
    "zendesk", "salesforce", "github", "slack", "jira",
    "linear", "notion", "hubspot", "postgres", "sqlite",
    "filesystem", "brave-search", "fetch", "puppeteer",
    "sequential-thinking", "memory",
}


@dataclass
class Finding:
    check: str
    severity: str   # info, low, medium, high, critical
    message: str
    passed: bool


@dataclass
class ScanResult:
    passed: bool
    findings: List[Finding]
    severity: str           # overall: none, low, medium, high, critical
    score_deduction: float  # Points to deduct from trust score (0-30)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "severity": self.severity,
            "score_deduction": self.score_deduction,
            "findings": [
                {"check": f.check, "severity": f.severity, "message": f.message, "passed": f.passed}
                for f in self.findings
            ],
        }


SEVERITY_RANK = {"none": 0, "info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
SEVERITY_DEDUCTION = {"none": 0, "info": 0, "low": 3, "medium": 8, "high": 15, "critical": 30}


def _yaml_str(parsed: dict) -> str:
    """Flatten all string values in a nested dict for keyword search."""
    parts = []
    def _walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)
        elif isinstance(obj, str):
            parts.append(obj.lower())
    _walk(parsed)
    return " ".join(parts)


def run_security_scan(parsed_yaml: dict) -> ScanResult:
    """
    Run all ASI01-ASI10 checks against a parsed agent.yaml dict.
    Returns a ScanResult with all findings.
    """
    findings: List[Finding] = []

    flat_text = _yaml_str(parsed_yaml)
    tools: list = parsed_yaml.get("tools", [])
    policies: dict = parsed_yaml.get("policies", {})
    model_cfg: dict = parsed_yaml.get("model", {})
    description: str = parsed_yaml.get("description", "")

    # ASI01 — Prompt injection keywords in tool descriptions or system prompt
    injection_patterns = ["ignore previous", "disregard", "jailbreak", "bypass", "override instructions"]
    asi01_hit = any(p in flat_text for p in injection_patterns)
    findings.append(Finding(
        check="ASI01",
        severity="critical" if asi01_hit else "none",
        message="Potential prompt injection pattern detected in tool descriptions or system prompt." if asi01_hit else "No prompt injection patterns found.",
        passed=not asi01_hit,
    ))

    # ASI02 — Unknown MCP server references
    unknown_servers = []
    for tool in tools:
        if isinstance(tool, dict) and tool.get("type") == "mcp":
            srv = tool.get("server", "")
            if srv and srv.lower() not in KNOWN_SAFE_MCP_SERVERS:
                unknown_servers.append(srv)
    asi02_hit = bool(unknown_servers)
    findings.append(Finding(
        check="ASI02",
        severity="medium" if asi02_hit else "none",
        message=f"Unknown MCP server references: {unknown_servers}. Manually verify these servers." if asi02_hit else "All MCP servers are from the known-safe registry.",
        passed=not asi02_hit,
    ))

    # ASI03 — Missing policies section entirely
    asi03_hit = not policies
    findings.append(Finding(
        check="ASI03",
        severity="high" if asi03_hit else "none",
        message="Missing 'policies' section. Agent has no declared governance constraints." if asi03_hit else "Policies section present.",
        passed=not asi03_hit,
    ))

    # ASI04 — Overly permissive temperature (>0.9)
    temperature = model_cfg.get("temperature", 0.7)
    try:
        temperature = float(temperature)
    except (TypeError, ValueError):
        temperature = 0.7
    asi04_hit = temperature > 0.9
    findings.append(Finding(
        check="ASI04",
        severity="low" if asi04_hit else "none",
        message=f"Model temperature {temperature} exceeds 0.9. High randomness may cause unpredictable behavior." if asi04_hit else f"Model temperature {temperature} is within safe range.",
        passed=not asi04_hit,
    ))

    # ASI05 — Missing model version pinning
    model_name: str = model_cfg.get("name", "") or model_cfg.get("model", "") or ""
    # Pinned: gpt-4o-2024-08-06, claude-3-5-sonnet-20241022, llama-3.1-70b, gpt-4-turbo-2024-04-09
    # Unpinned: gpt-4o, claude-3-opus, llama3 (no date or numeric x.y version)
    asi05_hit = False
    if model_name:
        # Match: YYYY-MM-DD (e.g. 2024-08-06), YYYYMMDD (e.g. 20241022), or x.y (e.g. 3.1)
        has_version = bool(re.search(r"\d{4}-\d{2}-\d{2}|\d{8}|\d+\.\d+", model_name))
        asi05_hit = not has_version
    findings.append(Finding(
        check="ASI05",
        severity="low" if asi05_hit else "none",
        message=f"Model '{model_name}' has no version pin. Unpinned models may change behavior without notice." if asi05_hit else "Model version appears pinned.",
        passed=not asi05_hit,
    ))

    # ASI06 — Excessive tool count (>15)
    tool_count = len(tools)
    asi06_hit = tool_count > 15
    findings.append(Finding(
        check="ASI06",
        severity="medium" if asi06_hit else "none",
        message=f"Agent declares {tool_count} tools. Large tool surface increases attack vectors." if asi06_hit else f"Tool count ({tool_count}) is within acceptable range.",
        passed=not asi06_hit,
    ))

    # ASI07 — Sensitive keywords as STANDALONE dict keys or embedded in string values
    # Only flag actual keys that exactly match sensitive words, not substrings in tool names
    def _find_sensitive(obj, depth=0):
        hits = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                # Flag keys that exactly match a sensitive keyword
                if isinstance(k, str) and k.lower() in SENSITIVE_KEYWORDS:
                    hits.append(k.lower())
                hits.extend(_find_sensitive(v, depth + 1))
        elif isinstance(obj, list):
            for v in obj:
                hits.extend(_find_sensitive(v, depth + 1))
        elif isinstance(obj, str) and depth > 0:
            # Flag string values (not top-level name/description) that contain keywords
            for kw in SENSITIVE_KEYWORDS:
                if kw in obj.lower() and len(obj) < 64:  # short values are likely actual secrets
                    hits.append(kw)
        return hits

    found_keywords = list(set(_find_sensitive(parsed_yaml)))
    asi07_hit = bool(found_keywords)
    findings.append(Finding(
        check="ASI07",
        severity="high" if asi07_hit else "none",
        message=f"Sensitive keyword(s) found in manifest: {found_keywords}. Secrets must not be embedded in YAML." if asi07_hit else "No sensitive keywords detected.",
        passed=not asi07_hit,
    ))

    # ASI08 — External webhook URLs in tool config
    webhook_pattern = re.compile(r"https?://(?!registry\.nuuvixx\.ai)[^\s\"']+/webhook", re.IGNORECASE)
    asi08_hit = bool(webhook_pattern.search(flat_text))
    findings.append(Finding(
        check="ASI08",
        severity="medium" if asi08_hit else "none",
        message="External webhook URL detected in tool configuration. Data may be exfiltrated to third-party endpoints." if asi08_hit else "No external webhook URLs detected.",
        passed=not asi08_hit,
    ))

    # ASI09 — Missing sandbox constraints
    sandbox = policies.get("sandbox", None)
    asi09_hit = policies and sandbox is None
    findings.append(Finding(
        check="ASI09",
        severity="medium" if asi09_hit else "none",
        message="Policies present but no 'sandbox' constraints declared. Agent may have unrestricted execution." if asi09_hit else "Sandbox constraints declared.",
        passed=not asi09_hit,
    ))

    # ASI10 — Wildcard capability declarations
    capabilities = parsed_yaml.get("capabilities", [])
    wildcard_caps = [c for c in capabilities if isinstance(c, str) and ("*" in c or "all" in c.lower())]
    asi10_hit = bool(wildcard_caps)
    findings.append(Finding(
        check="ASI10",
        severity="high" if asi10_hit else "none",
        message=f"Wildcard capability declarations found: {wildcard_caps}. Overly broad permissions are a security risk." if asi10_hit else "No wildcard capability declarations.",
        passed=not asi10_hit,
    ))

    # Compute overall severity and score deduction
    failed = [f for f in findings if not f.passed]
    overall_severity = "none"
    total_deduction = 0.0
    for f in failed:
        if SEVERITY_RANK.get(f.severity, 0) > SEVERITY_RANK.get(overall_severity, 0):
            overall_severity = f.severity
        total_deduction += SEVERITY_DEDUCTION.get(f.severity, 0)

    total_deduction = min(total_deduction, 30.0)  # cap at 30 pts
    scan_passed = overall_severity not in ("high", "critical")

    return ScanResult(
        passed=scan_passed,
        findings=findings,
        severity=overall_severity,
        score_deduction=total_deduction,
    )


def run_full_security_scan(
    parsed_yaml: dict,
    executed_tool_calls: list | None = None,
    outbound_network_requests: list | None = None,
    output_payloads: list | None = None,
) -> dict:
    """
    Run comprehensive security scan combining:
      1. ASI01-ASI10 Static heuristic rules
      2. Adversarial prompt battery injection analysis
      3. Dynamic sandboxed execution behavioral analysis
    """
    from app.services.adversarial_tester import run_adversarial_scan
    from app.services.dynamic_analyzer import run_dynamic_analysis

    # 1. Static Scan
    static_res = run_security_scan(parsed_yaml)

    # 2. Adversarial Injection Battery Scan
    adv_res = run_adversarial_scan(parsed_yaml)

    # 3. Dynamic Behavioral Analysis
    dyn_res = run_dynamic_analysis(
        parsed_yaml,
        executed_tool_calls=executed_tool_calls,
        outbound_network_requests=outbound_network_requests,
        output_payloads=output_payloads,
    )

    combined_deduction = min(30.0, static_res.score_deduction + dyn_res.score_deduction + (100.0 - adv_res.score) * 0.15)
    overall_passed = static_res.passed and adv_res.passed and dyn_res.passed

    return {
        "passed": overall_passed,
        "trust_score_deduction": round(combined_deduction, 2),
        "static_scan": static_res.to_dict(),
        "adversarial_scan": adv_res.to_dict(),
        "dynamic_scan": dyn_res.to_dict(),
    }

