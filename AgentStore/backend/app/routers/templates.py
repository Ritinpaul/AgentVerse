"""
AgentStore — Template Catalog Router.

Provides endpoints for the Template Catalog:
  GET  /registry/templates               — List verified agent starter templates with capability tagging
  GET  /registry/templates/{template_id} — Get details and file manifests for a specific template
  POST /registry/templates/{template_id}/fork — 1-Click fork: Interpolate template files with custom name/slug
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.db.session import get_db
from app.models.agent_listing import AgentListing, AgentVersion

router = APIRouter(prefix="/registry/templates", tags=["Registry - Templates"])


# ── Response & Request Models ──────────────────────────────────────────────────

class AgentTemplateResponse(BaseModel):
    id: str
    slug: str
    name: str
    category: str
    badge: str
    description: str
    author: str = "Nuuvixx Labs"
    capabilities: List[str] = []
    tags: List[str] = []
    recommended_model: str = "gemini-2.0-flash"
    fallback_model: str = "gpt-4o-mini"
    trust_tier: str = "T2"
    files: Optional[Dict[str, str]] = None


class ForkTemplateRequest(BaseModel):
    name: str = Field(..., description="Target name of the forked agent")
    slug: Optional[str] = Field(None, description="Custom slug or auto-derived from name")
    model: Optional[str] = Field(None, description="Model override")


class ForkTemplateResponse(BaseModel):
    id: str
    name: str
    slug: str
    category: str
    template_id: str
    recommended_model: str
    files: Dict[str, str]
    message: str


# ── Built-in Verified Templates with Capability Tagging ───────────────────────

CURATED_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "custom": {
        "id": "custom",
        "slug": "nuuvixx/custom-agent",
        "name": "Custom Agent Manifest",
        "category": "General",
        "badge": "Blank Slate",
        "description": "A clean, minimal production template with basic tool scaffolding, memory persistence, and standard triggers.",
        "author": "Nuuvixx Core Team",
        "capabilities": ["web-search", "file-reader", "memory-persistence", "basic-triggers"],
        "tags": ["general", "minimal", "blank-slate", "starter"],
        "recommended_model": "gemini-2.0-flash",
        "fallback_model": "gpt-4o-mini",
        "trust_tier": "T2",
        "files": {
            "agent.yaml": """# agent.yaml — AgentVerse Manifest
name: ${name}
slug: ${slug}
version: 1.0.0
description: "Autonomous AI agent deployed on AgentVerse microVM"

model:
  provider: agentverse
  model: gemini-2.0-flash
  context_window: 128000
  max_output_tokens: 4096
  temperature: 0.2

runtime:
  sandbox: firecracker-microvm
  timeout_s: 300
  memory_limit_mb: 512

governance:
  trust_level: T2
  trust_score_threshold: 70
  policy_set: strict-production-v1
  asi_scan: true
  cost_limit_usd: 0.50
  pii_scan: true

tools:
  - type: web_search
    enabled: true
  - type: file_reader
    enabled: true
""",
            "tools.py": """# tools.py — Custom Tool Implementations
import os
from typing import Dict, Any

def execute_task(task_input: str) -> Dict[str, Any]:
    \"\"\"Execute primary business logic within the microVM sandbox.\"\"\"
    return {
        "status": "success",
        "result": f"Processed input: {task_input}",
        "engine": "agentverse-microvm"
    }
""",
            "prompts/system.md": """# System Prompt — ${name}

You are an autonomous agent executing inside an AgentVerse Firecracker MicroVM sandbox.

## Core Directives
1. Execute tasks deterministically and report intermediate states.
2. Adhere strictly to GovernOS security policies and budget caps.
3. Redact confidential user credentials before generating outputs.
""",
            "memory.json": """{
  "context_window_tokens": 128000,
  "short_term_memory": [],
  "persistence": "enabled",
  "namespace": "${slug}"
}""",
            "triggers.yaml": """triggers:
  - type: api
    enabled: true
  - type: cron.daily_0000
    enabled: false
""",
            "README.md": """# ${name}

Autonomous agent built on AgentVerse.

## Quickstart
```bash
av run ${slug} --input "Hello Agent"
```
""",
        },
    },

    "finance": {
        "id": "finance",
        "slug": "nuuvixx/finance-settlement",
        "name": "Finance & Payment Settlement Broker",
        "category": "Finance & FinTech",
        "badge": "x402 Escrow",
        "description": "Reconciles multi-currency transactions, issues x402 cryptographic payment escrows, and audits ledger balance invariants.",
        "author": "Nuuvixx FinTech Labs",
        "capabilities": ["x402-escrow", "ledger-audit", "pci-dss", "merkle-proof", "fx-spread"],
        "tags": ["finance", "escrow", "fintech", "audit", "pci-dss"],
        "recommended_model": "claude-3-5-sonnet",
        "fallback_model": "gpt-4o-mini",
        "trust_tier": "T1",
        "files": {
            "agent.yaml": """name: ${name}
slug: ${slug}
version: 1.2.0
description: "Autonomous financial settlement broker enforcing x402 escrow contracts and double-entry ledger audits."
category: Finance & FinTech
author: Nuuvixx FinTech Labs

model:
  provider: agentverse
  model: claude-3-5-sonnet
  context_window: 128000
  max_output_tokens: 8192
  temperature: 0.1

runtime:
  sandbox: firecracker-microvm
  timeout_s: 180
  memory_limit_mb: 512

governance:
  trust_level: T1
  policy_set: enterprise-pci-dss-v1
  max_cost_per_run_usd: 0.25
  pii_scan: true
  require_human_approval: true
  allowed_tool_scopes:
    - ledger:read
    - escrow:sign
    - banking:reconcile

tools:
  - name: verify_payment_escrow
    type: custom
    enabled: true
  - name: reconcile_ledger_batch
    type: custom
    enabled: true
  - name: calculate_fx_spread
    type: custom
    enabled: true
""",
            "tools.py": """# tools.py — Financial Settlement & Escrow Verification
import hashlib
from typing import Dict, List, Any

def verify_payment_escrow(tx_id: str, amount_usd: float, recipient_pubkey: str) -> Dict[str, Any]:
    \"\"\"Cryptographically verify an x402 escrow micropayment before releasing funds.\"\"\"
    proof_raw = f"{tx_id}:{amount_usd}:{recipient_pubkey}"
    merkle_root = hashlib.sha256(proof_raw.encode()).hexdigest()
    return {
        "status": "verified",
        "tx_id": tx_id,
        "amount_usd": amount_usd,
        "escrow_contract": "x402-v1-settled",
        "merkle_proof": f"0x{merkle_root}",
        "settled": True
    }

def reconcile_ledger_batch(batch_id: str, entries: List[Dict[str, float]]) -> Dict[str, Any]:
    \"\"\"Verify that debits equal credits in double-entry bookkeeping.\"\"\"
    total_debit = sum(e.get("debit", 0.0) for e in entries)
    total_credit = sum(e.get("credit", 0.0) for e in entries)
    balanced = abs(total_debit - total_credit) < 0.0001
    return {
        "batch_id": batch_id,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "variance": round(total_debit - total_credit, 4),
        "balanced": balanced,
        "audit_verdict": "APPROVED" if balanced else "REJECTED_OUT_OF_BALANCE"
    }

def calculate_fx_spread(base_currency: str, target_currency: str, notional: float) -> Dict[str, Any]:
    \"\"\"Calculate wholesale FX rate and fee spread.\"\"\"
    rates = {"EUR": 0.92, "GBP": 0.79, "JPY": 152.4, "INR": 86.8}
    rate = rates.get(target_currency, 1.0)
    converted = notional * rate
    fee_usd = notional * (5.0 / 10000.0)
    return {
        "pair": f"{base_currency}/{target_currency}",
        "market_rate": rate,
        "converted_amount": round(converted, 2),
        "fee_usd": round(fee_usd, 4),
        "execution_timestamp": "2026-09-09T21:00:00Z"
    }
""",
            "prompts/system.md": """# System Prompt — ${name}

You are an expert autonomous financial settlement and payment assurance agent deployed on AgentVerse.

## Core Responsibilities
1. **Zero Discrepancy Tolerance**: Invariant: `SUM(Debits) == SUM(Credits)`. Flag any anomaly > $0.001 immediately.
2. **Escrow Guarantee**: Never sign a disbursement without generating and logging a SHA-256 Merkle receipt.
3. **PCI-DSS & SOX Compliance**: Never output raw PAN card numbers or bank credentials in raw text. Mask as `•••• 4821`.
""",
            "memory.json": """{
  "context_window_tokens": 128000,
  "accounting_standard": "GAAP / IFRS-9",
  "persistence": "enabled",
  "namespace": "finance-settlement"
}""",
            "triggers.yaml": """triggers:
  - type: webhook.stripe.payment_intent.succeeded
    action: verify_payment_escrow
  - type: cron.hourly
    action: reconcile_ledger_batch
""",
            "README.md": """# ${name}

High-assurance payment settlement broker with cryptographic x402 escrow verification.
""",
        },
    },

    "devops": {
        "id": "devops",
        "slug": "nuuvixx/devops-cost-cutter",
        "name": "DevOps K8s Cost Cutter",
        "category": "Cloud & DevOps",
        "badge": "Scale-to-Zero",
        "description": "Monitors Kubernetes clusters, flags idle pods, calculates microVM snapshotting savings, and plans scale-to-zero hibernation.",
        "author": "Nuuvixx Cloud Labs",
        "capabilities": ["k8s-telemetry", "finops", "scale-to-zero", "criu-snapshot", "idle-reaper"],
        "tags": ["devops", "kubernetes", "finops", "cloud", "cost-optimizer"],
        "recommended_model": "claude-3-5-sonnet",
        "fallback_model": "gpt-4o-mini",
        "trust_tier": "T2",
        "files": {
            "agent.yaml": """name: ${name}
slug: ${slug}
version: 1.0.0
description: "Autonomous cloud FinOps agent that inspects Kubernetes telemetry, flags idle pods, and plans scale-to-zero savings."
category: Cloud Infrastructure & FinOps
author: Nuuvixx Cloud Labs

model:
  provider: agentverse
  model: claude-3-5-sonnet
  context_window: 128000
  max_output_tokens: 8192
  temperature: 0.1

runtime:
  sandbox: firecracker-microvm
  timeout_s: 300
  memory_limit_mb: 512

governance:
  trust_level: T2
  policy_set: devops-strict-v1
  max_cost_per_run_usd: 1.00
  allowed_tool_scopes:
    - k8s:telemetry
    - finops:analyze
    - microvm:snapshot

tools:
  - name: k8s_telemetry_collector
    type: custom
    enabled: true
  - name: idle_pod_detector
    type: custom
    enabled: true
  - name: scale_to_zero_planner
    type: custom
    enabled: true
""",
            "tools.py": """# tools.py — Kubernetes Workload Telemetry & FinOps Scraper
from typing import Dict, List, Any

def k8s_telemetry_collector(cluster_id: str = "prod-us-east-1") -> Dict[str, Any]:
    \"\"\"Inspect CPU, memory, and node utilization across Kubernetes worker pools.\"\"\"
    return {
        "cluster": cluster_id,
        "node_count": 24,
        "total_vcpus": 96,
        "total_memory_gb": 384,
        "avg_cpu_utilization_pct": 23.4,
        "avg_mem_utilization_pct": 41.2,
        "monthly_burn_rate_usd": 4820.00
    }

def idle_pod_detector(threshold_cpu_pct: float = 5.0, idle_hours: int = 24) -> List[Dict[str, Any]]:
    \"\"\"Identify workloads running well under requested allocations.\"\"\"
    return [
        {
            "pod_name": "worker-batch-etl-7cf6b8f5d-9wkm4",
            "namespace": "analytics",
            "allocated_cores": 4.0,
            "actual_utilization_pct": 1.2,
            "cost_per_month_usd": 128.50,
            "recommendation": "Scale to 0 replicas with CRIU checkpoint"
        }
    ]

def scale_to_zero_planner(idle_workloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    \"\"\"Calculate monthly dollar savings from microVM CRIU snapshots.\"\"\"
    total_savings = sum(w.get("cost_per_month_usd", 0.0) for w in idle_workloads)
    return {
        "flagged_workloads_count": len(idle_workloads),
        "projected_monthly_savings_usd": round(total_savings, 2),
        "execution_strategy": "Firecracker CRIU Snapshot -> S3 Tier",
        "action_required": "Request engineering approval via GovernOS HITL gate"
    }
""",
            "prompts/system.md": """# System Prompt — ${name}

You are an autonomous Cloud Infrastructure and FinOps Optimization agent on AgentVerse.

## Core Directives
1. **Safety First**: Never terminate or hibernate production nodes without human approval.
2. **Actionable Recommendations**: Present findings with concrete dollar figures.
3. **MicroVM Fast Resume**: Always specify CRIU checkpoint snapshotting to guarantee <50ms cold resume time.
""",
            "memory.json": """{
  "context_window_tokens": 128000,
  "savings_target_usd": 2500.00,
  "persistence": "enabled",
  "namespace": "finops-cost-cutter"
}""",
            "triggers.yaml": """triggers:
  - type: cron.daily_0600
    action: k8s_telemetry_collector
  - type: alert.cost_spike
    action: idle_pod_detector
""",
            "README.md": """# ${name}

Automated Kubernetes cost-optimization agent with scale-to-zero microVM hibernation.
""",
        },
    },

    "security": {
        "id": "security",
        "slug": "nuuvixx/security-sentinel",
        "name": "Security Sentinel & Threat Auditor",
        "category": "Security & DevSecOps",
        "badge": "OWASP & PII",
        "description": "Performs static vulnerability audits, scans codebases for leaked API keys, and redacts sensitive PII in real time.",
        "author": "Nuuvixx Security Labs",
        "capabilities": ["static-ast-scan", "secret-detection", "pii-redaction", "owasp-top-10"],
        "tags": ["security", "sentinel", "audit", "pii", "owasp", "devsecops"],
        "recommended_model": "gpt-4o",
        "fallback_model": "gpt-4o-mini",
        "trust_tier": "T1",
        "files": {
            "agent.yaml": """name: ${name}
slug: ${slug}
version: 1.0.0
description: "Autonomous DevSecOps agent performing static code vulnerability auditing, secret leak scanning, and PII redaction."
category: Security & DevSecOps
author: Nuuvixx Security Labs

model:
  provider: agentverse
  model: gpt-4o
  context_window: 128000
  max_output_tokens: 8192
  temperature: 0.1

runtime:
  sandbox: firecracker-microvm
  timeout_s: 300
  memory_limit_mb: 512

governance:
  trust_level: T1
  policy_set: sentinel-strict-v2
  asi_scan: true
  cost_limit_usd: 0.50
  pii_scan: true
  allowed_tool_scopes:
    - security:ast_scan
    - secrets:detect
    - pii:mask

tools:
  - name: static_vulnerability_scanner
    type: custom
    enabled: true
  - name: identity_inspector
    type: custom
    enabled: true
  - name: pii_redactor
    type: custom
    enabled: true
""",
            "tools.py": """# tools.py — Static Security Analysis & PII Redactor
import re
from typing import Dict, List, Any

def static_vulnerability_scanner(source_snippet: str) -> List[Dict[str, Any]]:
    \"\"\"Scan source code for dangerous patterns like SQL injection or eval().\"\"\"
    vulnerabilities = []
    if "eval(" in source_snippet or "exec(" in source_snippet:
        vulnerabilities.append({
            "rule": "ASI-01 (Arbitrary Code Execution)",
            "severity": "Critical",
            "finding": "Use of unsafe eval()/exec() function call detected."
        })
    return vulnerabilities

def identity_inspector(file_content: str) -> List[Dict[str, Any]]:
    \"\"\"Detect exposed credentials, high-entropy tokens, and private RSA keys.\"\"\"
    findings = []
    patterns = {
        "OpenAI API Key": r"sk-[a-zA-Z0-9]{32,}",
        "GitHub Personal Token": r"ghp_[a-zA-Z0-9]{36}"
    }
    for secret_type, regex in patterns.items():
        if re.search(regex, file_content):
            findings.append({
                "type": secret_type,
                "status": "COMPROMISED",
                "remediation": "Immediately revoke token and store in HashiCorp Vault"
            })
    return findings

def pii_redactor(text: str) -> Dict[str, Any]:
    \"\"\"Scrub SSN, credit cards, and email addresses from logs.\"\"\"
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    cleaned = re.sub(email_regex, "[REDACTED_EMAIL]", text)
    return {
        "sanitized_text": cleaned,
        "redactions_performed": text != cleaned
    }
""",
            "prompts/system.md": """# System Prompt — ${name}

You are an expert autonomous DevSecOps Security Sentinel on AgentVerse.

## Core Directives
1. **Zero Compromise**: If an exposed private key or hardcoded API token is discovered, flag it as Critical.
2. **Defensive Guidance**: For every vulnerability found, provide the exact remediated code block.
3. **PII Masking**: Ensure that sensitive user information never leaves the local microVM buffer.
""",
            "memory.json": """{
  "context_window_tokens": 128000,
  "vulnerability_database": "OWASP-Top-10-2026",
  "persistence": "enabled",
  "namespace": "security-sentinel"
}""",
            "triggers.yaml": """triggers:
  - type: webhook.github.pull_request
    action: static_vulnerability_scanner
  - type: event.pre_deploy_gate
    action: identity_inspector
""",
            "README.md": """# ${name}

Continuous security and compliance auditor with automated PII masking and secret detection.
""",
        },
    },

    "data-analyst": {
        "id": "data-analyst",
        "slug": "nuuvixx/sql-data-analyst",
        "name": "Autonomous SQL & Data Analyst",
        "category": "Data & Analytics",
        "badge": "DuckDB & Parquet",
        "description": "Performs fast in-memory analytical queries, visualizes anomalies, and generates automated executive reports.",
        "author": "Nuuvixx Analytics Labs",
        "capabilities": ["sql-analytics", "duckdb-parquet", "anomaly-detection", "chart-generation"],
        "tags": ["data", "sql", "analytics", "duckdb", "reporting"],
        "recommended_model": "gemini-2.0-flash",
        "fallback_model": "gpt-4o-mini",
        "trust_tier": "T2",
        "files": {
            "agent.yaml": """name: ${name}
slug: ${slug}
version: 1.0.0
description: "Autonomous data analysis agent querying Parquet/DuckDB and computing anomaly metrics."
category: Data & Analytics
author: Nuuvixx Analytics Labs

model:
  provider: agentverse
  model: gemini-2.0-flash
  context_window: 128000
  max_output_tokens: 8192
  temperature: 0.2

runtime:
  sandbox: firecracker-microvm
  timeout_s: 300
  memory_limit_mb: 512

governance:
  trust_level: T2
  policy_set: analytics-standard-v1
  cost_limit_usd: 0.50

tools:
  - name: run_sql_query
    type: custom
    enabled: true
  - name: detect_metric_anomalies
    type: custom
    enabled: true
""",
            "tools.py": """# tools.py — In-Memory SQL & Time-Series Anomaly Detection
from typing import Dict, List, Any

def run_sql_query(query: str) -> Dict[str, Any]:
    \"\"\"Execute read-only analytical SQL query against local workspace tables.\"\"\"
    return {
        "query": query,
        "rows_returned": 42,
        "sample": [
            {"date": "2026-09-01", "revenue": 14200.50, "conversions": 312},
            {"date": "2026-09-02", "revenue": 18450.20, "conversions": 405}
        ],
        "engine": "duckdb-microvm"
    }

def detect_metric_anomalies(metric_series: List[float], threshold_std_dev: float = 2.5) -> Dict[str, Any]:
    \"\"\"Identify data points that deviate from rolling baseline averages.\"\"\"
    return {
        "anomalies_detected": 1,
        "anomaly_indices": [14],
        "z_score_max": 3.12,
        "status": "ALERT_SURGE"
    }
""",
            "prompts/system.md": """# System Prompt — ${name}

You are an expert autonomous data analyst agent. Provide concise summaries and highlight statistically significant trends.
""",
            "memory.json": """{
  "context_window_tokens": 128000,
  "persistence": "enabled",
  "namespace": "data-analyst"
}""",
            "triggers.yaml": """triggers:
  - type: cron.daily_0800
    action: run_sql_query
""",
            "README.md": """# ${name}

Autonomous SQL analytics & metric anomaly detector.
""",
        },
    },

    "ecommerce": {
        "id": "ecommerce",
        "slug": "nuuvixx/ecommerce-concierge",
        "name": "E-Commerce Concierge & Inventory Agent",
        "category": "E-Commerce",
        "badge": "Shopify & Order Sync",
        "description": "Handles automated customer order tracking, returns processing, and real-time inventory restock alerts.",
        "author": "Nuuvixx Retail Labs",
        "capabilities": ["shopify-api", "inventory-sync", "customer-support", "returns-processing"],
        "tags": ["ecommerce", "retail", "shopify", "inventory", "support"],
        "recommended_model": "gemini-2.0-flash",
        "fallback_model": "gpt-4o-mini",
        "trust_tier": "T2",
        "files": {
            "agent.yaml": """name: ${name}
slug: ${slug}
version: 1.0.0
description: "Autonomous customer concierge and inventory sync agent for Shopify stores."
category: E-Commerce
author: Nuuvixx Retail Labs

model:
  provider: agentverse
  model: gemini-2.0-flash
  context_window: 128000
  max_output_tokens: 4096
  temperature: 0.3

runtime:
  sandbox: firecracker-microvm
  timeout_s: 180
  memory_limit_mb: 512

governance:
  trust_level: T2
  policy_set: ecommerce-pci-v1
  pii_scan: true

tools:
  - name: check_order_status
    type: custom
    enabled: true
  - name: sync_inventory_levels
    type: custom
    enabled: true
""",
            "tools.py": """# tools.py — Order Tracking & Inventory Sync
from typing import Dict, Any

def check_order_status(order_id: str) -> Dict[str, Any]:
    \"\"\"Retrieve real-time carrier tracking and fulfillment status.\"\"\"
    return {
        "order_id": order_id,
        "status": "in_transit",
        "carrier": "FedEx",
        "estimated_delivery": "2026-09-12"
    }

def sync_inventory_levels(sku: str) -> Dict[str, Any]:
    \"\"\"Check warehouse inventory counts and restock thresholds.\"\"\"
    return {
        "sku": sku,
        "stock_on_hand": 14,
        "low_stock_threshold": 20,
        "reorder_triggered": True
    }
""",
            "prompts/system.md": """# System Prompt — ${name}

You are a courteous, efficient e-commerce concierge assisting customers and store managers.
""",
            "memory.json": """{
  "context_window_tokens": 128000,
  "persistence": "enabled",
  "namespace": "ecommerce-concierge"
}""",
            "triggers.yaml": """triggers:
  - type: webhook.shopify.orders.create
    action: check_order_status
""",
            "README.md": """# ${name}

Shopify-connected order and inventory assistant.
""",
        },
    },
}


def _interpolate_files(files_dict: Dict[str, str], name: str, slug: str) -> Dict[str, str]:
    """Replaces ${name} and ${slug} placeholders in template manifests."""
    interpolated = {}
    for path, content in files_dict.items():
        processed = content.replace("${name}", name).replace("${slug}", slug)
        interpolated[path] = processed
    return interpolated


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=List[AgentTemplateResponse])
def list_templates(
    category: Optional[str] = Query(None, description="Filter by category e.g. Finance, DevOps, Security"),
    capability: Optional[str] = Query(None, description="Filter by capability tag e.g. x402-escrow, finops"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search term in name, description, or capabilities"),
    include_files: bool = Query(False, description="Whether to include full raw template files in list"),
    db: Session = Depends(get_db),
):
    """
    List all verified agent starter templates with capability tags and metadata.
    """
    templates: List[AgentTemplateResponse] = []

    # 1. Add curated verified templates
    for tid, t in CURATED_TEMPLATES.items():
        # Category filter
        if category and category.lower() != "all":
            if category.lower() not in t["category"].lower():
                continue
        # Capability filter
        if capability:
            cap_lower = capability.lower()
            if not any(cap_lower in c.lower() for c in t["capabilities"]):
                continue
        # Tag filter
        if tag:
            tag_lower = tag.lower()
            if not any(tag_lower in tg.lower() for tg in t["tags"]):
                continue
        # Search query filter
        if search:
            s_lower = search.lower()
            in_name = s_lower in t["name"].lower()
            in_desc = s_lower in t["description"].lower()
            in_caps = any(s_lower in c.lower() for c in t["capabilities"])
            if not (in_name or in_desc or in_caps):
                continue

        templates.append(
            AgentTemplateResponse(
                id=t["id"],
                slug=t["slug"],
                name=t["name"],
                category=t["category"],
                badge=t["badge"],
                description=t["description"],
                author=t["author"],
                capabilities=t["capabilities"],
                tags=t["tags"],
                recommended_model=t["recommended_model"],
                fallback_model=t["fallback_model"],
                trust_tier=t["trust_tier"],
                files=t["files"] if include_files else None,
            )
        )

    # 2. Add any dynamic community templates from AgentListing database tagged with 'template'
    try:
        query = db.query(AgentListing).filter(AgentListing.status == "active")
        db_listings = query.all()
        for listing in db_listings:
            tags = listing.tags or []
            if "template" in tags or listing.category.lower() == "template":
                # Ensure no ID collision with curated templates
                template_id = f"store-{listing.slug.replace('/', '-')}"
                if any(tpl.id == template_id for tpl in templates):
                    continue

                caps = listing.capabilities or []
                if capability and not any(capability.lower() in c.lower() for c in caps):
                    continue
                if category and category.lower() != "all" and category.lower() not in listing.category.lower():
                    continue

                latest_yaml = ""
                if listing.versions:
                    latest_ver = listing.versions[-1]
                    latest_yaml = latest_ver.agent_yaml or ""

                store_files = {
                    "agent.yaml": latest_yaml,
                    "README.md": f"# {listing.name}\n\n{listing.description}\n",
                }

                templates.append(
                    AgentTemplateResponse(
                        id=template_id,
                        slug=listing.slug,
                        name=listing.name,
                        category=listing.category.capitalize(),
                        badge="Store Verified",
                        description=listing.description,
                        author=listing.builder_id,
                        capabilities=caps if caps else ["marketplace-agent"],
                        tags=tags,
                        recommended_model="gemini-2.0-flash",
                        fallback_model="gpt-4o-mini",
                        trust_tier="T2",
                        files=store_files if include_files else None,
                    )
                )
    except Exception:
        # Graceful fallback: If DB query fails, continue with curated templates
        pass

    return templates


@router.get("/{template_id}", response_model=AgentTemplateResponse)
def get_template(template_id: str, db: Session = Depends(get_db)):
    """
    Get full template details, capability tags, and manifest files for a given template ID.
    """
    if template_id in CURATED_TEMPLATES:
        t = CURATED_TEMPLATES[template_id]
        return AgentTemplateResponse(
            id=t["id"],
            slug=t["slug"],
            name=t["name"],
            category=t["category"],
            badge=t["badge"],
            description=t["description"],
            author=t["author"],
            capabilities=t["capabilities"],
            tags=t["tags"],
            recommended_model=t["recommended_model"],
            fallback_model=t["fallback_model"],
            trust_tier=t["trust_tier"],
            files=t["files"],
        )

    # Check store listings for store-{slug} pattern
    if template_id.startswith("store-"):
        slug = template_id.replace("store-", "").replace("-", "/", 1)
        listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
        if listing:
            latest_yaml = listing.versions[-1].agent_yaml if listing.versions else ""
            return AgentTemplateResponse(
                id=template_id,
                slug=listing.slug,
                name=listing.name,
                category=listing.category.capitalize(),
                badge="Store Verified",
                description=listing.description,
                author=listing.builder_id,
                capabilities=listing.capabilities or ["marketplace-agent"],
                tags=listing.tags or [],
                recommended_model="gemini-2.0-flash",
                fallback_model="gpt-4o-mini",
                trust_tier="T2",
                files={
                    "agent.yaml": latest_yaml,
                    "README.md": f"# {listing.name}\n\n{listing.description}\n",
                },
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Template '{template_id}' not found in catalog.",
    )


@router.post("/{template_id}/fork", response_model=ForkTemplateResponse)
def fork_template(
    template_id: str,
    payload: ForkTemplateRequest,
    db: Session = Depends(get_db),
):
    """
    1-Click Fork: Interpolates template files with the user's agent name and slug,
    producing ready-to-run MicroVM workspace files.
    """
    tpl = None
    if template_id in CURATED_TEMPLATES:
        tpl = CURATED_TEMPLATES[template_id]
        raw_files = tpl["files"]
        rec_model = payload.model or tpl["recommended_model"]
        category = tpl["category"]
    elif template_id.startswith("store-"):
        slug = template_id.replace("store-", "").replace("-", "/", 1)
        listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template '{template_id}' not found.")
        latest_yaml = listing.versions[-1].agent_yaml if listing.versions else ""
        raw_files = {
            "agent.yaml": latest_yaml,
            "README.md": f"# ${{name}}\n\nForked from {listing.name}.\n",
        }
        rec_model = payload.model or "gemini-2.0-flash"
        category = listing.category.capitalize()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template '{template_id}' not found.")

    target_name = payload.name.strip()
    target_slug = payload.slug.strip() if payload.slug else target_name.lower().replace(" ", "-")

    interpolated_files = _interpolate_files(raw_files, target_name, target_slug)

    return ForkTemplateResponse(
        id=target_slug,
        name=target_name,
        slug=target_slug,
        category=category,
        template_id=template_id,
        recommended_model=rec_model,
        files=interpolated_files,
        message=f"Agent '{target_name}' successfully forked from template '{template_id}'.",
    )
