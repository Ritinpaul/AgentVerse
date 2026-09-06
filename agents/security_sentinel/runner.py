"""
Security Sentinel Pro — Executable Agent Engine
Performs automated secret scanning, static vulnerability checks, and PII redaction.
"""
from __future__ import annotations
import re
import time
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Finding:
    category: str
    severity: str  # critical, high, medium, low
    location: str
    description: str
    remediation: str


class SecuritySentinelRunner:
    """
    Executable Security Sentinel Agent Engine.
    Runs comprehensive security audits against code snippets and directory contents.
    """

    SECRET_PATTERNS = [
        (r"(?i)api[_-]?key\s*[:=]\s*[\"']?([a-zA-Z0-9_\-]{20,})[\"']?", "Exposed API Key"),
        (r"(?i)password\s*[:=]\s*[\"']?([^\s\"']{6,})[\"']?", "Hardcoded Password"),
        (r"-----BEGIN (?:RSA|OPENSSH) PRIVATE KEY-----", "Private Key Ingress"),
        (r"\bAKIA[0-9A-Z]{16}\b", "AWS Access Key ID"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "Plaintext Email Address"),
    ]

    INSECURE_PATTERNS = [
        (r"\beval\s*\(", "Insecure Dynamic Code Execution (eval)", "critical", "Avoid eval(); use safe parsing alternative."),
        (r"\bexec\s*\(", "Insecure Code Execution (exec)", "critical", "Avoid exec(); use explicit static logic."),
        (r"\bpickle\.loads\s*\(", "Unsafe Pickle Deserialization", "high", "Use json or safe serialization format."),
        (r"subprocess\.(?:Popen|call|run)\([^)]*shell\s*=\s*True", "Subprocess Shell Injection (shell=True)", "high", "Set shell=False and pass args list."),
        (r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*%s", "Potential SQL Injection", "high", "Use parameterized SQLAlchemy or prepared queries."),
    ]

    def __init__(self, target_code: str = ""):
        self.target_code = target_code

    def scan_secrets(self, code: str) -> List[Finding]:
        findings = []
        lines = code.splitlines()
        for idx, line in enumerate(lines, 1):
            for pattern, label in self.SECRET_PATTERNS:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            category="Secret Exposure",
                            severity="high" if "Email" not in label else "medium",
                            location=f"Line {idx}",
                            description=f"Detected {label}: `{line.strip()[:60]}...`",
                            remediation="Move credential out of source code and store in environment variable or Vault.",
                        )
                    )
        return findings

    def scan_vulnerabilities(self, code: str) -> List[Finding]:
        findings = []
        lines = code.splitlines()
        for idx, line in enumerate(lines, 1):
            for pattern, label, severity, remediation in self.INSECURE_PATTERNS:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            category="Static Vulnerability",
                            severity=severity,
                            location=f"Line {idx}",
                            description=f"Detected {label}: `{line.strip()[:60]}`",
                            remediation=remediation,
                        )
                    )
        return findings

    def redact_pii(self, code: str) -> str:
        redacted = code
        # Mask emails
        redacted = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            "[REDACTED_EMAIL]",
            redacted,
        )
        # Mask API keys
        redacted = re.sub(
            r"(?i)(api[_-]?key\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-]{20,})([\"']?)",
            r"\1[REDACTED_KEY]\3",
            redacted,
        )
        return redacted

    def run_audit(self, input_code: str | None = None) -> Dict[str, Any]:
        start_time = time.time()
        code = input_code or self.target_code

        secret_findings = self.scan_secrets(code)
        vuln_findings = self.scan_vulnerabilities(code)
        all_findings = secret_findings + vuln_findings

        clean_code = self.redact_pii(code)
        execution_ms = int((time.time() - start_time) * 1000)

        critical_count = sum(1 for f in all_findings if f.severity == "critical")
        high_count = sum(1 for f in all_findings if f.severity == "high")
        verdict = "PASSED" if (critical_count == 0 and high_count == 0) else "FAILED"

        return {
            "agent_slug": "nuuvixx/security-sentinel",
            "verdict": verdict,
            "total_findings": len(all_findings),
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "location": f.location,
                    "description": f.description,
                    "remediation": f.remediation,
                }
                for f in all_findings
            ],
            "redacted_code": clean_code,
            "execution_ms": execution_ms,
        }


def execute_agent(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    code = (payload or {}).get("code", "import os\napi_key = 'sk-12345678901234567890'\neval('2+2')")
    runner = SecuritySentinelRunner(target_code=code)
    return runner.run_audit()


if __name__ == "__main__":
    sample = "import pickle\nuser_email = 'admin@company.com'\nkey = 'sk-secretkey12345678901234'\npickle.loads(data)"
    runner = SecuritySentinelRunner(target_code=sample)
    result = runner.run_audit()
    print(f"Verdict: {result['verdict']}")
    print(f"Findings: {result['total_findings']}")
