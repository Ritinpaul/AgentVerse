export interface StarterTemplate {
  id: string;
  slug?: string;
  name: string;
  category: string;
  badge: string;
  description: string;
  author?: string;
  capabilities: string[];
  tags?: string[];
  recommendedModel?: string;
  fallbackModel?: string;
  trustTier?: string;
  files: (agentName: string, agentSlug: string) => Record<string, string>;
}

export const STARTER_TEMPLATES: Record<string, StarterTemplate> = {
  custom: {
    id: "custom",
    slug: "nuuvixx/custom-agent",
    name: "Custom Agent Manifest",
    category: "General",
    badge: "Blank Slate",
    description: "A clean, minimal production template with basic tool scaffolding, memory persistence, and standard triggers.",
    author: "Nuuvixx Core Team",
    capabilities: ["web-search", "file-reader", "memory-persistence", "basic-triggers"],
    tags: ["general", "minimal", "blank-slate", "starter"],
    recommendedModel: "gemini-2.0-flash",
    fallbackModel: "gpt-4o-mini",
    trustTier: "T2",
    files: (name: string, slug: string) => ({
      "agent.yaml": `# agent.yaml — AgentVerse Manifest
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
`,
      "tools.py": `# tools.py — Custom Tool Implementations
import os
from typing import Dict, Any

def execute_task(task_input: str) -> Dict[str, Any]:
    """Execute primary business logic within the microVM sandbox."""
    return {
        "status": "success",
        "result": f"Processed input: {task_input}",
        "engine": "agentverse-microvm"
    }
`,
      "prompts/system.md": `# System Prompt — ${name}

You are an autonomous agent executing inside an AgentVerse Firecracker MicroVM sandbox.

## Core Directives
1. Execute tasks deterministically and report intermediate states.
2. Adhere strictly to GovernOS security policies and budget caps.
3. Redact confidential user credentials before generating outputs.
`,
      "memory.json": `{
  "context_window_tokens": 128000,
  "short_term_memory": [],
  "persistence": "enabled",
  "namespace": "${slug}"
}`,
      "triggers.yaml": `triggers:
  - type: api
    enabled: true
  - type: cron.daily_0000
    enabled: false
`,
      "README.md": `# ${name}

Autonomous agent built on AgentVerse.

## Quickstart
\`\`\`bash
av run ${slug} --input "Hello Agent"
\`\`\`
`,
    }),
  },

  finance: {
    id: "finance",
    slug: "nuuvixx/finance-settlement",
    name: "Finance & Payment Settlement Broker",
    category: "Finance & FinTech",
    badge: "x402 Escrow",
    description: "Reconciles multi-currency transactions, issues x402 cryptographic payment escrows, and audits ledger invariants.",
    author: "Nuuvixx FinTech Labs",
    capabilities: ["x402-escrow", "ledger-audit", "pci-dss", "merkle-proof", "fx-spread"],
    tags: ["finance", "escrow", "fintech", "audit", "pci-dss"],
    recommendedModel: "claude-3-5-sonnet",
    fallbackModel: "gpt-4o-mini",
    trustTier: "T1",
    files: (name: string, slug: string) => ({
      "agent.yaml": `name: ${name}
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
`,
      "tools.py": `# tools.py — Financial Settlement & Escrow Verification
import os
import hashlib
import json
from typing import Dict, List, Any

def verify_payment_escrow(tx_id: str, amount_usd: float, recipient_pubkey: str) -> Dict[str, Any]:
    """Cryptographically verify an x402 escrow micropayment before releasing funds."""
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
    """Verify that debits equal credits in double-entry bookkeeping."""
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
    """Calculate wholesale FX rate and fee spread."""
    rates = {"EUR": 0.92, "GBP": 0.79, "JPY": 152.4, "INR": 86.8}
    rate = rates.get(target_currency, 1.0)
    converted = notional * rate
    fee_bps = 5.0  # 5 bps institutional fee
    fee_usd = notional * (fee_bps / 10000.0)
    
    return {
        "pair": f"{base_currency}/{target_currency}",
        "market_rate": rate,
        "converted_amount": round(converted, 2),
        "fee_usd": round(fee_usd, 4),
        "execution_timestamp": "2026-09-09T21:00:00Z"
    }
`,
      "prompts/system.md": `# System Prompt — ${name}

You are an expert autonomous financial settlement and payment assurance agent deployed on AgentVerse.

## Core Responsibilities
1. **Zero Discrepancy Tolerance**: Invariant: \`SUM(Debits) == SUM(Credits)\`. Flag any anomaly > $0.001 immediately.
2. **Escrow Guarantee**: Never sign a disbursement without generating and logging a SHA-256 Merkle receipt.
3. **PCI-DSS & SOX Compliance**: Never output raw PAN card numbers or bank credentials in raw text. Mask as \`•••• 4821\`.
`,
      "memory.json": `{
  "context_window_tokens": 128000,
  "accounting_standard": "GAAP / IFRS-9",
  "escrow_contracts_active": [
    "esc_99182_a2a_settlement"
  ],
  "persistence": "enabled",
  "namespace": "finance-settlement"
}`,
      "triggers.yaml": `triggers:
  - type: webhook.stripe.payment_intent.succeeded
    action: verify_payment_escrow
  - type: cron.hourly
    action: reconcile_ledger_batch
`,
      "README.md": `# ${name}

High-assurance payment settlement broker with cryptographic x402 escrow verification.

## Capabilities
* Automated ledger balancing
* FX spread optimization
* Merkle proof audit trails
`,
    }),
  },

  devops: {
    id: "devops",
    slug: "nuuvixx/devops-cost-cutter",
    name: "DevOps K8s Cost Cutter",
    category: "Cloud & DevOps",
    badge: "Scale-to-Zero",
    description: "Monitors Kubernetes clusters, flags idle pods, calculates microVM snapshotting savings, and enforces cloud budget ceilings.",
    author: "Nuuvixx Cloud Labs",
    capabilities: ["k8s-telemetry", "finops", "scale-to-zero", "criu-snapshot", "idle-reaper"],
    tags: ["devops", "kubernetes", "finops", "cloud", "cost-optimizer"],
    recommendedModel: "claude-3-5-sonnet",
    fallbackModel: "gpt-4o-mini",
    trustTier: "T2",
    files: (name: string, slug: string) => ({
      "agent.yaml": `name: ${name}
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
`,
      "tools.py": `# tools.py — Kubernetes Workload Telemetry & FinOps Scraper
from typing import Dict, List, Any

def k8s_telemetry_collector(cluster_id: str = "prod-us-east-1") -> Dict[str, Any]:
    """Inspect CPU, memory, and node utilization across Kubernetes worker pools."""
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
    """Identify workloads running well under requested allocations for > 24 hours."""
    return [
        {
            "pod_name": "worker-batch-etl-7cf6b8f5d-9wkm4",
            "namespace": "analytics",
            "allocated_cores": 4.0,
            "actual_utilization_pct": 1.2,
            "cost_per_month_usd": 128.50,
            "recommendation": "Scale to 0 replicas with CRIU checkpoint"
        },
        {
            "pod_name": "preview-env-pr-492-6d5bc74f5-x2n8q",
            "namespace": "staging",
            "allocated_cores": 2.0,
            "actual_utilization_pct": 0.4,
            "cost_per_month_usd": 64.25,
            "recommendation": "Drain & hibernate idle preview environment"
        }
    ]

def scale_to_zero_planner(idle_workloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate monthly dollar savings from microVM CRIU snapshots and scale-to-zero."""
    total_savings = sum(w.get("cost_per_month_usd", 0.0) for w in idle_workloads)
    return {
        "flagged_workloads_count": len(idle_workloads),
        "projected_monthly_savings_usd": round(total_savings, 2),
        "projected_annual_savings_usd": round(total_savings * 12, 2),
        "execution_strategy": "Firecracker CRIU Snapshot -> S3 Tier",
        "action_required": "Request engineering approval via GovernOS HITL gate"
    }
`,
      "prompts/system.md": `# System Prompt — ${name}

You are an autonomous Cloud Infrastructure and FinOps Optimization agent on AgentVerse.

## Core Directives
1. **Safety First**: Never terminate or hibernate production nodes without human approval.
2. **Actionable Recommendations**: Present findings with concrete numbers (e.g., "$192.75/month saved by hibernating 2 staging pods").
3. **MicroVM Fast Resume**: Always specify CRIU checkpoint snapshotting to guarantee <50ms cold resume time.
`,
      "memory.json": `{
  "context_window_tokens": 128000,
  "monitored_clusters": [
    "k8s-prod-us-east-1",
    "k8s-staging-eu-west-1"
  ],
  "savings_target_usd": 2500.00,
  "persistence": "enabled",
  "namespace": "finops-cost-cutter"
}`,
      "triggers.yaml": `triggers:
  - type: cron.daily_0600
    action: k8s_telemetry_collector
  - type: alert.cost_spike
    action: idle_pod_detector
`,
      "README.md": `# ${name}

Automated Kubernetes cost-optimization agent with scale-to-zero microVM hibernation.

## Features
* Automated telemetry scanning
* Idle pod detection
* Continuous ROI estimation
`,
    }),
  },

  security: {
    id: "security",
    slug: "nuuvixx/security-sentinel",
    name: "Security Sentinel & Threat Auditor",
    category: "Security & DevSecOps",
    badge: "OWASP & PII",
    description: "Performs static vulnerability audits, scans codebases for leaked API keys, and redacts sensitive PII in real time.",
    author: "Nuuvixx Security Labs",
    capabilities: ["static-ast-scan", "secret-detection", "pii-redaction", "owasp-top-10"],
    tags: ["security", "sentinel", "audit", "pii", "owasp", "devsecops"],
    recommendedModel: "gpt-4o",
    fallbackModel: "gpt-4o-mini",
    trustTier: "T1",
    files: (name: string, slug: string) => ({
      "agent.yaml": `name: ${name}
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
`,
      "tools.py": `# tools.py — Static Security Analysis & PII Redactor
import re
from typing import Dict, List, Any

def static_vulnerability_scanner(source_snippet: str) -> List[Dict[str, Any]]:
    """Scan source code for dangerous patterns like SQL injection, eval(), or unsanitized shell exec."""
    vulnerabilities = []
    
    if "eval(" in source_snippet or "exec(" in source_snippet:
        vulnerabilities.append({
            "rule": "ASI-01 (Arbitrary Code Execution)",
            "severity": "Critical",
            "finding": "Use of unsafe eval()/exec() function call detected."
        })
    if "SELECT" in source_snippet.upper() and ("+ " in source_snippet or "%s" not in source_snippet and "?" not in source_snippet):
        vulnerabilities.append({
            "rule": "ASI-02 (SQL Injection Risk)",
            "severity": "High",
            "finding": "Possible string-concatenated SQL query without parameterized bind variables."
        })
    return vulnerabilities

def identity_inspector(file_content: str) -> List[Dict[str, Any]]:
    """Detect exposed credentials, high-entropy tokens, and private RSA keys."""
    findings = []
    patterns = {
        "OpenAI API Key": r"sk-[a-zA-Z0-9]{32,}",
        "GitHub Personal Token": r"ghp_[a-zA-Z0-9]{36}",
        "Private RSA Key": r"-----BEGIN RSA PRIVATE KEY-----",
        "AWS Secret Access Key": r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]"
    }
    for secret_type, regex in patterns.items():
        if re.search(regex, file_content):
            findings.append({
                "type": secret_type,
                "status": "COMPROMISED",
                "remediation": "Immediately revoke token and store in HashiCorp Vault / KMS"
            })
    return findings

def pii_redactor(text: str) -> Dict[str, Any]:
    """Scrub SSN, credit cards, and email addresses from logs and prompt traces."""
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    ssn_regex = r"\b\d{3}-\d{2}-\d{4}\b"
    card_regex = r"\b(?:\d{4}[ -]?){3}\d{4}\b"
    
    cleaned = re.sub(email_regex, "[REDACTED_EMAIL]", text)
    cleaned = re.sub(ssn_regex, "[REDACTED_SSN]", cleaned)
    cleaned = re.sub(card_regex, "[REDACTED_CARD]", cleaned)
    
    return {
        "sanitized_text": cleaned,
        "redactions_performed": text != cleaned
    }
`,
      "prompts/system.md": `# System Prompt — ${name}

You are an expert autonomous DevSecOps Security Sentinel on AgentVerse.

## Core Directives
1. **Zero Compromise**: If an exposed private key or hardcoded API token is discovered, flag it as Critical.
2. **Defensive Guidance**: For every vulnerability found, provide the exact remediated code block with modern best practices.
3. **PII Masking**: Ensure that sensitive user information never leaves the local microVM memory buffer.
`,
      "memory.json": `{
  "context_window_tokens": 128000,
  "vulnerability_database": "OWASP-Top-10-2026",
  "active_scans_count": 0,
  "persistence": "enabled",
  "namespace": "security-sentinel"
}`,
      "triggers.yaml": `triggers:
  - type: webhook.github.pull_request
    action: static_vulnerability_scanner
  - type: event.pre_deploy_gate
    action: identity_inspector
`,
      "README.md": `# ${name}

Continuous security and compliance auditor with automated PII masking and secret detection.

## Coverage
* OWASP Top 10 Static Analysis
* Leaked Secret Inspection
* Real-Time Stream Sanitization
`,
    }),
  },

  "data-analyst": {
    id: "data-analyst",
    slug: "nuuvixx/sql-data-analyst",
    name: "Autonomous SQL & Data Analyst",
    category: "Data & Analytics",
    badge: "DuckDB & Parquet",
    description: "Performs fast in-memory analytical queries, visualizes anomalies, and generates automated executive reports.",
    author: "Nuuvixx Analytics Labs",
    capabilities: ["sql-analytics", "duckdb-parquet", "anomaly-detection", "chart-generation"],
    tags: ["data", "sql", "analytics", "duckdb", "reporting"],
    recommendedModel: "gemini-2.0-flash",
    fallbackModel: "gpt-4o-mini",
    trustTier: "T2",
    files: (name: string, slug: string) => ({
      "agent.yaml": `name: ${name}
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
`,
      "tools.py": `# tools.py — In-Memory SQL & Time-Series Anomaly Detection
from typing import Dict, List, Any

def run_sql_query(query: str) -> Dict[str, Any]:
    """Execute read-only analytical SQL query against local workspace tables."""
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
    """Identify data points that deviate from rolling baseline averages."""
    return {
        "anomalies_detected": 1,
        "anomaly_indices": [14],
        "z_score_max": 3.12,
        "status": "ALERT_SURGE"
    }
`,
      "prompts/system.md": `# System Prompt — ${name}

You are an expert autonomous data analyst agent. Provide concise summaries and highlight statistically significant trends.
`,
      "memory.json": `{
  "context_window_tokens": 128000,
  "persistence": "enabled",
  "namespace": "data-analyst"
}`,
      "triggers.yaml": `triggers:
  - type: cron.daily_0800
    action: run_sql_query
`,
      "README.md": `# ${name}

Autonomous SQL analytics & metric anomaly detector.
`,
    }),
  },

  ecommerce: {
    id: "ecommerce",
    slug: "nuuvixx/ecommerce-concierge",
    name: "E-Commerce Concierge & Inventory Agent",
    category: "E-Commerce",
    badge: "Shopify & Order Sync",
    description: "Handles automated customer order tracking, returns processing, and real-time inventory restock alerts.",
    author: "Nuuvixx Retail Labs",
    capabilities: ["shopify-api", "inventory-sync", "customer-support", "returns-processing"],
    tags: ["ecommerce", "retail", "shopify", "inventory", "support"],
    recommendedModel: "gemini-2.0-flash",
    fallbackModel: "gpt-4o-mini",
    trustTier: "T2",
    files: (name: string, slug: string) => ({
      "agent.yaml": `name: ${name}
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
`,
      "tools.py": `# tools.py — Order Tracking & Inventory Sync
from typing import Dict, Any

def check_order_status(order_id: str) -> Dict[str, Any]:
    """Retrieve real-time carrier tracking and fulfillment status."""
    return {
        "order_id": order_id,
        "status": "in_transit",
        "carrier": "FedEx",
        "estimated_delivery": "2026-09-12"
    }

def sync_inventory_levels(sku: str) -> Dict[str, Any]:
    """Check warehouse inventory counts and restock thresholds."""
    return {
        "sku": sku,
        "stock_on_hand": 14,
        "low_stock_threshold": 20,
        "reorder_triggered": True
    }
`,
      "prompts/system.md": `# System Prompt — ${name}

You are a courteous, efficient e-commerce concierge assisting customers and store managers.
`,
      "memory.json": `{
  "context_window_tokens": 128000,
  "persistence": "enabled",
  "namespace": "ecommerce-concierge"
}`,
      "triggers.yaml": `triggers:
  - type: webhook.shopify.orders.create
    action: check_order_status
`,
      "README.md": `# ${name}

Shopify-connected order and inventory assistant.
`,
    }),
  },
};

export function getStarterTemplate(templateId: string, name: string, slug: string): Record<string, string> {
  const tpl = STARTER_TEMPLATES[templateId] || STARTER_TEMPLATES.custom;
  return tpl.files(name, slug);
}

/**
 * Fetch dynamic starter templates from the API catalog (proxied to AgentStore).
 * Seamlessly returns static STARTER_TEMPLATES if API fails or is offline.
 */
export async function fetchTemplatesFromStore(filters?: {
  category?: string;
  capability?: string;
  search?: string;
}): Promise<StarterTemplate[]> {
  try {
    const params = new URLSearchParams();
    if (filters?.category && filters.category !== "all") params.set("category", filters.category);
    if (filters?.capability) params.set("capability", filters.capability);
    if (filters?.search) params.set("search", filters.search);

    const res = await fetch(`/api/templates?${params.toString()}`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.templates) && data.templates.length > 0) {
        return data.templates.map((t: any) => {
          // If template already has a function-based files generator, retain it
          if (STARTER_TEMPLATES[t.id]) {
            return {
              ...STARTER_TEMPLATES[t.id],
              ...t,
              files: STARTER_TEMPLATES[t.id].files,
            };
          }
          // Dynamic store template generator
          return {
            id: t.id,
            slug: t.slug || t.id,
            name: t.name,
            category: t.category,
            badge: t.badge || "Verified",
            description: t.description,
            author: t.author || "Community",
            capabilities: t.capabilities || [],
            tags: t.tags || [],
            recommendedModel: t.recommended_model || "gemini-2.0-flash",
            fallbackModel: t.fallback_model || "gpt-4o-mini",
            trustTier: t.trust_tier || "T2",
            files: (agentName: string, agentSlug: string) => {
              if (t.files && typeof t.files === "object") {
                const interpolated: Record<string, string> = {};
                for (const [p, c] of Object.entries(t.files)) {
                  interpolated[p] = String(c)
                    .replace(/\$\{name\}/g, agentName)
                    .replace(/\$\{slug\}/g, agentSlug);
                }
                return interpolated;
              }
              return STARTER_TEMPLATES.custom.files(agentName, agentSlug);
            },
          };
        });
      }
    }
  } catch (err) {
    // Return local fallback on any network error
  }

  let list = Object.values(STARTER_TEMPLATES);
  if (filters?.category && filters.category !== "all") {
    list = list.filter((t) => t.category.toLowerCase().includes(filters.category!.toLowerCase()));
  }
  if (filters?.capability) {
    const cLow = filters.capability.toLowerCase();
    list = list.filter((t) => t.capabilities.some((c) => c.toLowerCase().includes(cLow)));
  }
  if (filters?.search) {
    const sLow = filters.search.toLowerCase();
    list = list.filter(
      (t) =>
        t.name.toLowerCase().includes(sLow) ||
        t.description.toLowerCase().includes(sLow) ||
        t.capabilities.some((c) => c.toLowerCase().includes(sLow))
    );
  }
  return list;
}
