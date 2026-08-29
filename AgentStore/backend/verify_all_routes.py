"""
AgentStore End-to-End Live Route Verification Suite
Tests all API routes on http://127.0.0.1:8005 for status, response schemas, and data quality.
"""
import sys
import json
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8005"

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


passed_count = 0
failed_count = 0


def verify(name: str, method: str, path: str, payload=None, expected_status: int = 200, validators=None):
    global passed_count, failed_count
    url = f"{BASE_URL}{path}"
    try:
        if method.upper() == "GET":
            resp = httpx.get(url, timeout=5.0)
        elif method.upper() == "POST":
            resp = httpx.post(url, json=payload, timeout=5.0)
        elif method.upper() == "PUT":
            resp = httpx.put(url, json=payload, timeout=5.0)
        else:
            raise ValueError(f"Unsupported method {method}")

        status_ok = resp.status_code == expected_status
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text

        validation_ok = True
        validation_msgs = []
        if status_ok and validators and isinstance(data, (dict, list)):
            for val_fn, desc in validators:
                try:
                    if not val_fn(data):
                        validation_ok = False
                        validation_msgs.append(f"Validation failed: {desc}")
                except Exception as e:
                    validation_ok = False
                    validation_msgs.append(f"Validation exception: {desc} ({e})")

        if status_ok and validation_ok:
            passed_count += 1
            print(f"  {Colors.GREEN}[PASS]{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET} ({method} {path}) -> HTTP {resp.status_code}")
        else:
            failed_count += 1
            print(f"  {Colors.RED}[FAIL]{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET} ({method} {path}) -> HTTP {resp.status_code}")
            if not status_ok:
                print(f"      {Colors.YELLOW}Expected status {expected_status}, got {resp.status_code}{Colors.RESET}")
            for msg in validation_msgs:
                print(f"      {Colors.YELLOW}{msg}{Colors.RESET}")
            if isinstance(data, dict):
                print(f"      Response snippet: {json.dumps(data)[:200]}")

        return data

    except Exception as e:
        failed_count += 1
        print(f"  {Colors.RED}[ERROR]{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET} ({method} {path}) -> {e}")
        return None


def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}==============================================================={Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}       AgentStore Live API Verification Suite (Phases 1-6)       {Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}==============================================================={Colors.RESET}\n")

    # ── Phase 1: Foundation Registry & Search ─────────────────────────────────
    print(f"{Colors.BOLD}--- Phase 1: Foundation Registry & Search ---{Colors.RESET}")
    verify("Root Status Endpoint", "GET", "/", validators=[
        (lambda d: d.get("status") == "online", "status is 'online'"),
        (lambda d: "phases" in d, "contains phase roadmap list"),
    ])

    verify("List Registry Agents", "GET", "/api/v1/registry/agents", validators=[
        (lambda d: isinstance(d, list) and len(d) >= 1, "returns non-empty agent list"),
        (lambda d: "slug" in d[0] and "trust_score" in d[0], "agent item has required fields"),
    ])

    verify("Agent Detail (nuuvixx/security-sentinel)", "GET", "/api/v1/registry/agents/nuuvixx/security-sentinel", validators=[
        (lambda d: d.get("slug") == "nuuvixx/security-sentinel", "slug matches request"),
        (lambda d: "versions" in d, "contains version history"),
    ])

    verify("Semantic Capability Search", "GET", "/api/v1/search?q=security", validators=[
        (lambda d: isinstance(d, list), "returns list of search results"),
    ])

    verify("CLI Run Helper", "GET", "/api/v1/cli/run/nuuvixx/security-sentinel", validators=[
        (lambda d: "command" in d and "nuuvixx" in d["command"], "contains nuuvixx CLI command"),
    ])

    # ── Phase 2: Verification & Trust ──────────────────────────────────────────
    print(f"\n{Colors.BOLD}--- Phase 2: Verification & Trust ---{Colors.RESET}")
    verify("Trigger Security Scan (ASI01-ASI10)", "POST", "/api/v1/verification/agents/nuuvixx/security-sentinel/scan/trigger", validators=[
        (lambda d: "scan" in d and "findings" in d["scan"], "contains scan findings"),
        (lambda d: len(d["scan"]["findings"]) == 10, "scans all 10 ASI rules"),
        (lambda d: "trust_score" in d, "computes trust score"),
    ])

    verify("Get Security Scan Findings", "GET", "/api/v1/verification/agents/nuuvixx/security-sentinel/scan", validators=[
        (lambda d: d.get("passed") is True, "scan passed status"),
        (lambda d: "score_deduction" in d, "contains score deduction"),
    ])

    verify("Declare Compliance Badge", "POST", "/api/v1/verification/agents/nuuvixx/security-sentinel/badges", expected_status=201, payload={
        "badge_type": "soc2",
        "evidence_url": "https://evidence.nuuvixx.ai/soc2.pdf"
    }, validators=[
        (lambda d: d.get("badge_type") == "soc2", "badge_type matches declared type"),
        (lambda d: "id" in d, "returns badge ID"),
    ])

    verify("List Compliance Badges", "GET", "/api/v1/verification/agents/nuuvixx/security-sentinel/badges", validators=[
        (lambda d: isinstance(d, list) and len(d) >= 1, "returns list containing declared badge"),
    ])

    verify("Builder Profile (KYC)", "GET", "/api/v1/verification/builders/nuuvixx/profile", validators=[
        (lambda d: d.get("builder_id") == "nuuvixx", "builder_id matches"),
        (lambda d: "kyc_status" in d, "contains KYC status"),
    ])

    verify("Report Incident", "POST", "/api/v1/incidents/", expected_status=201, payload={
        "listing_id": 1,
        "reporter_id": "security-tester",
        "severity": "low",
        "description": "Minor tool timeout edge case report."
    }, validators=[
        (lambda d: "incident_id" in d, "returns incident ID"),
        (lambda d: "score_penalty_applied" in d, "applies score penalty"),
    ])

    verify("List Incidents", "GET", "/api/v1/incidents/", validators=[
        (lambda d: isinstance(d, list) and len(d) >= 1, "returns non-empty incident list"),
    ])

    # ── Phase 3: Monetization & Pricing ───────────────────────────────────────
    print(f"\n{Colors.BOLD}--- Phase 3: Monetization & Pricing ---{Colors.RESET}")
    verify("Subscription Tiers", "GET", "/api/v1/pricing/tiers", validators=[
        (lambda d: len(d) == 3, "returns exactly 3 tiers (Free, Pro, Enterprise)"),
        (lambda d: d[1]["tier"] == "pro", "Pro tier exists"),
    ])

    verify("Agent Pricing Config", "GET", "/api/v1/pricing/agents/nuuvixx/security-sentinel", validators=[
        (lambda d: "free_tier_runs" in d and "price_per_run" in d, "returns pricing parameters"),
    ])

    verify("Record Execution Metering", "POST", "/api/v1/billing/meter", payload={
        "listing_id": 1,
        "org_id": "corp-live-test",
        "caller_id": "user-verify",
        "duration_ms": 1200,
        "tokens_used": 1500
    }, validators=[
        (lambda d: d.get("allowed") is True, "execution allowed"),
        (lambda d: "cost_usd" in d and d["cost_usd"] > 0, "calculates non-zero cost"),
    ])

    verify("Org Subscription Plan", "GET", "/api/v1/billing/orgs/corp-live-test/plan", validators=[
        (lambda d: d.get("tier") == "free", "initial tier is free"),
        (lambda d: d.get("runs_used_this_month") >= 1, "usage counter updated"),
    ])

    verify("Org Usage Summary", "GET", "/api/v1/billing/orgs/corp-live-test/usage", validators=[
        (lambda d: "runs_used" in d and "total_cost_usd" in d, "returns usage & cost totals"),
    ])

    verify("Builder Revenue (80/20 Split)", "GET", "/api/v1/billing/builders/nuuvixx/revenue", validators=[
        (lambda d: "gross_revenue_usd" in d and "net_revenue_usd" in d, "returns gross & net totals"),
        (lambda d: abs(d["net_revenue_usd"] - (d["gross_revenue_usd"] * 0.8)) < 0.001, "verifies 80/20 builder split"),
    ])

    # ── Phase 4: Composability ────────────────────────────────────────────────
    print(f"\n{Colors.BOLD}--- Phase 4: Composability & Lockfiles ---{Colors.RESET}")
    verify("Ad-Hoc Dependency Resolution", "POST", "/api/v1/compositions/resolve-deps", payload={
        "agent_slugs": ["nuuvixx/security-sentinel"]
    }, validators=[
        (lambda d: "resolved" in d and "lockfile" in d, "returns resolution and lockfile"),
        (lambda d: "integrity_hash" in d["lockfile"], "generates SHA-256 lockfile integrity hash"),
    ])

    verify("Cross-Agent Policy Validation", "POST", "/api/v1/compositions/validate-policies", payload={
        "agent_slugs": ["nuuvixx/security-sentinel"]
    }, validators=[
        (lambda d: "valid" in d and "clashes" in d, "returns policy validity and clash list"),
    ])

    # ── Phase 5: Enterprise Procurement ───────────────────────────────────────
    print(f"\n{Colors.BOLD}--- Phase 5: Enterprise Procurement ---{Colors.RESET}")
    proc_req = verify("Submit Procurement Request", "POST", "/api/v1/procurement/requests", expected_status=201, payload={
        "org_id": "bank-corp",
        "requester_id": "alice.manager",
        "agent_slug": "nuuvixx/security-sentinel",
        "tier": "pro",
        "justification": "Customer support automation"
    }, validators=[
        (lambda d: d.get("stage") == "security_review", "initial stage is security_review"),
        (lambda d: d.get("status") == "pending", "initial status is pending"),
    ])

    req_id = proc_req.get("id") if proc_req else None
    if req_id:
        verify("Advance Workflow (security_review -> policy_check)", "PUT", f"/api/v1/procurement/requests/{req_id}/advance", payload={
            "approver_id": "sec-officer",
            "action": "approve"
        }, validators=[
            (lambda d: d.get("stage") == "policy_check", "advanced stage to policy_check"),
        ])

    verify("List Procurement Requests", "GET", "/api/v1/procurement/requests?org_id=bank-corp", validators=[
        (lambda d: isinstance(d, list) and len(d) >= 1, "returns non-empty request list"),
    ])

    verify("Private Catalog", "GET", "/api/v1/procurement/private-catalog/bank-corp", validators=[
        (lambda d: "approved_slugs" in d and "restricted_slugs" in d, "contains catalog lists"),
    ])

    verify("CFO Dashboard Metrics", "GET", "/api/v1/procurement/cfo-dashboard/bank-corp", validators=[
        (lambda d: "total_monthly_budget_usd" in d and "departments" in d, "returns budget and department metrics"),
    ])

    # ── Phase 6: Agent-to-Agent (A2A) Commerce ────────────────────────────────
    print(f"\n{Colors.BOLD}--- Phase 6: Agent-to-Agent Commerce & x402 ---{Colors.RESET}")
    verify("Advertise A2A Capability", "POST", "/api/v1/a2a/directory/advertise", expected_status=201, payload={
        "agent_slug": "nuuvixx/security-sentinel",
        "capability": "lookup:ticket",
        "endpoint_url": "http://127.0.0.1:8005/a2a/tickets",
        "price_per_call_x402": 0.001
    }, validators=[
        (lambda d: d.get("capability") == "lookup:ticket", "capability registered"),
    ])

    verify("Search Capability Directory", "GET", "/api/v1/a2a/directory", validators=[
        (lambda d: isinstance(d, list) and len(d) >= 1, "returns advertised capabilities"),
    ])

    contract = verify("Negotiate A2A Service Contract", "POST", "/api/v1/a2a/contracts/negotiate", expected_status=201, payload={
        "buyer_slug": "sales/lead-qualifier",
        "seller_slug": "nuuvixx/security-sentinel",
        "capability": "lookup:ticket"
    }, validators=[
        (lambda d: "contract_id" in d and d["contract_id"].startswith("ct_"), "returns contract ID"),
        (lambda d: d.get("status") == "agreed", "contract status is agreed"),
    ])

    contract_id = contract.get("contract_id") if contract else None
    if contract_id:
        verify("Settle x402 Micropayment", "POST", "/api/v1/a2a/contracts/settle", payload={
            "contract_id": contract_id,
            "output_data": "ticket_lookup_results_verified"
        }, validators=[
            (lambda d: d.get("status") == "settled", "contract settled"),
            (lambda d: d.get("x402_tx_hash", "").startswith("x402_tx_"), "generates x402 payment transaction hash"),
            (lambda d: d.get("output_hash", "").startswith("sha256:"), "generates output SHA-256 hash"),
        ])

    verify("Cryptographic Provenance Audit Trail", "GET", "/api/v1/a2a/audit-trail", validators=[
        (lambda d: isinstance(d, list) and len(d) >= 1, "returns provenance audit log items"),
        (lambda d: "payload_hash" in d[0], "log item contains cryptographic payload_hash"),
    ])

    # ── Summary Report ────────────────────────────────────────────────────────
    total_tests = passed_count + failed_count
    print(f"\n{Colors.BOLD}{Colors.CYAN}==============================================================={Colors.RESET}")
    print(f"{Colors.BOLD}Verification Results Summary:{Colors.RESET}")
    print(f"  Total Routes Verified : {total_tests}")
    print(f"  {Colors.GREEN}Passed                : {passed_count}{Colors.RESET}")
    print(f"  {Colors.RED}Failed / Error        : {failed_count}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}==============================================================={Colors.RESET}\n")

    if failed_count > 0:
        sys.exit(1)
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}[SUCCESS] ALL ROUTES VERIFIED UP TO MARK WITH 100% SUCCESS RATE!{Colors.RESET}\n")


if __name__ == "__main__":
    main()
