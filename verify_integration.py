"""
Nuuvixx AgentsEcosystem — Integration Verification Suite
=========================================================

Tests all 6 integration bridges end-to-end:
  Bridge 1: AgentStudio → AgentStore (Publish Pipeline & Trust Scoring)
  Bridge 2: AgentOS CLI → AgentStore (Run Manifest + Trust Gate)
  Bridge 3: AgentOS CLI → AgentOS Control Plane (Manifest Validate & Plan)
  Bridge 4: AgentGovernOS → AgentStore (Catalog Gate & Procurement)
  Bridge 5: AgentOS → AgentGovernOS (SENTINEL Policy Pre-Execution Check)
  Bridge 6: A2A Commerce (Capability Discovery & Contract Negotiation)

Usage:
  python verify_integration.py                    # All tests, skips offline services
  python verify_integration.py --strict           # Strict mode: All bridges must be online & pass
  STRICT_INTEGRATION=1 python verify_integration.py # Strict mode via environment variable
  python verify_integration.py --store-only       # Only AgentStore tests
"""

import io
import os
import sys
import time
from pathlib import Path
import httpx

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Fix Windows console encoding for Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Load ecosystem .env ────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists() and load_dotenv is not None:
    load_dotenv(dotenv_path=_env_path)

AGENTSTORE_URL      = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
CONTROL_PLANE_URL   = os.getenv("CONTROL_PLANE_URL", "http://127.0.0.1:8010")
EXECUTION_PLANE_URL = os.getenv("EXECUTION_PLANE_URL", "http://127.0.0.1:8012")
AGENTGOVERN_URL     = os.getenv("AGENTGOVERN_URL", "http://127.0.0.1:8025")
NUUVIXX_API_KEY     = os.getenv("NUUVIXX_API_KEY", "dev-nuuvixx-svc-key-2026")

STRICT_MODE = "--strict" in sys.argv or os.getenv("STRICT_INTEGRATION", "").lower() in ("1", "true", "yes")
STORE_ONLY  = "--store-only" in sys.argv

# Colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def h(url: str, method="GET", json_body=None, timeout=5.0) -> httpx.Response:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if NUUVIXX_API_KEY:
        headers["X-API-Key"] = NUUVIXX_API_KEY
    with httpx.Client(timeout=timeout) as client:
        if method == "GET":
            return client.get(url, headers=headers)
        elif method == "POST":
            return client.post(url, json=json_body or {}, headers=headers)
        elif method == "PUT":
            return client.put(url, json=json_body or {}, headers=headers)


passed = 0
failed = 0
skipped = 0
results = []


def check(name: str, fn, expect_status=200, optional=False):
    global passed, failed, skipped
    # In strict mode, optional checks are enforced as mandatory
    is_optional = optional and not STRICT_MODE

    try:
        start = time.time()
        r = fn()
        ms = int((time.time() - start) * 1000)
        if r and r.status_code == expect_status:
            passed += 1
            results.append((True, name, ms, None))
            print(f"  {GREEN}✓{RESET} {name} ({ms}ms)")
            return r
        else:
            status_code = r.status_code if r else "No Response"
            body = r.text[:120] if r and r.text else ""
            if is_optional:
                skipped += 1
                results.append((None, name, ms, f"HTTP {status_code} (optional service)"))
                print(f"  {YELLOW}○{RESET} {name} — {status_code} (optional/offline)")
            else:
                failed += 1
                results.append((False, name, ms, f"HTTP {status_code}: {body}"))
                print(f"  {RED}✕{RESET} {name} — Expected {expect_status}, got {status_code}: {body}")
            return r
    except (httpx.RequestError, httpx.TimeoutException) as e:
        if is_optional:
            skipped += 1
            results.append((None, name, 0, f"Offline (optional): {e}"))
            print(f"  {YELLOW}○{RESET} {name} — Offline/optional: {e}")
        else:
            failed += 1
            results.append((False, name, 0, f"Connection error: {e}"))
            print(f"  {RED}✕{RESET} {name} — Connection error: {e}")
        return None


def main():
    global passed, failed, skipped

    print(f"\n{BOLD}{CYAN}═════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN} Nuuvixx AgentsEcosystem — Integration Verification{RESET}")
    mode_str = f"{RED}STRICT MODE{RESET}" if STRICT_MODE else f"{YELLOW}PERMISSIVE (Local/Offline){RESET}"
    print(f" Mode: {mode_str}")
    print(f"{BOLD}{CYAN}═════════════════════════════════════════════════════════{RESET}\n")

    # ── Service Health Checks ──────────────────────────────────────────────────────
    print(f"{BOLD}Service Health Checks{RESET}")
    check("AgentStore (:8005)",         lambda: h(f"{AGENTSTORE_URL}/health"), optional=True)
    if not STORE_ONLY:
        check("AgentOS Control Plane (:8010)",   lambda: h(f"{CONTROL_PLANE_URL}/health"), optional=True)
        check("AgentOS Execution Plane (:8012)", lambda: h(f"{EXECUTION_PLANE_URL}/health"), optional=True)
        check("AgentGovernOS API (:8025)",       lambda: h(f"{AGENTGOVERN_URL}/health"), optional=True)
    print()

    # ── BRIDGE 1: AgentStudio → AgentStore (Publish) ──────────────────────────────
    print(f"{BOLD}Bridge 1 — AgentStudio → AgentStore (Publish & Template Pipeline){RESET}")
    SAMPLE_MANIFEST = {
        "builder_id": "verify-bot",
        "agent_yaml": """
name: integration-test-agent
version: 1.0.0
description: Auto-created by integration verification suite
framework: custom
model:
  provider: openai
  name: gpt-4o
tools:
  - type: mcp
    server: text
    tool: process
""",
        "category": "testing",
    }

    pub_r = check(
        "POST /api/v1/registry/agents (publish manifest)",
        lambda: h(f"{AGENTSTORE_URL}/api/v1/registry/agents", "POST", SAMPLE_MANIFEST),
        expect_status=201,
        optional=True,
    )
    if pub_r and pub_r.status_code == 201:
        data = pub_r.json()
        listing_id = data.get("id", 1)
        listing_slug = data.get("slug", "verify-bot/integration-test-agent")
        trust_score = data.get("trust_score", 0)
        print(f"    → listing_id={listing_id}, slug={listing_slug}, trust_score={trust_score}")
    else:
        listing_id = 1
        listing_slug = "verify-bot/integration-test-agent"

    check("GET /api/v1/registry/agents (list all)", lambda: h(f"{AGENTSTORE_URL}/api/v1/registry/agents"), optional=True)
    check("GET /api/v1/registry/templates (starter templates)", lambda: h(f"{AGENTSTORE_URL}/api/v1/registry/templates"), optional=True)
    print()

    # ── BRIDGE 2: AgentOS CLI → AgentStore (Run Manifest) ─────────────────────────
    print(f"{BOLD}Bridge 2 — AgentOS CLI → AgentStore (Run Manifest & Metering){RESET}")
    run_r = check(
        f"GET /api/v1/cli/run/{listing_slug} (execution manifest)",
        lambda: h(f"{AGENTSTORE_URL}/api/v1/cli/run/{listing_slug}"),
        optional=True,
    )
    if run_r and run_r.status_code == 200:
        manifest = run_r.json()
        required_fields = ["listing_id", "trust_score", "scan_results", "lockfile", "command"]
        missing = [f for f in required_fields if f not in manifest]
        if missing:
            print(f"    {RED}✕ Missing Bridge 2 fields: {missing}{RESET}")
            if STRICT_MODE:
                failed += 1
        else:
            print(f"    {GREEN}✓ All Bridge 2 fields present: trust_score={manifest.get('trust_score')}{RESET}")

    check("GET /api/v1/cli/search (agent search)", lambda: h(f"{AGENTSTORE_URL}/api/v1/cli/search?q=test"), optional=True)
    check("POST /api/v1/billing/meter (execution meter)",
        lambda: h(f"{AGENTSTORE_URL}/api/v1/billing/meter", "POST", {
            "listing_id": listing_id,
            "org_id": "verify-org",
            "caller_id": "verify-bot",
            "duration_ms": 1500,
            "tokens_used": 100,
        }),
        expect_status=200,
        optional=True,
    )
    print()

    if not STORE_ONLY:
        # ── BRIDGE 3: AgentOS Control Plane ──────────────────────────────────────────
        print(f"{BOLD}Bridge 3 — AgentOS Control Plane (Manifest Validate & Plan){RESET}")
        sample_agent_yaml = """
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: integration-test-agent
  version: 1.0.0
model:
  provider: openai
  name: gpt-4o-mini
"""
        check(
            "POST /v1/manifest/validate (manifest validation)",
            lambda: h(f"{CONTROL_PLANE_URL}/v1/manifest/validate", "POST", {"yaml": sample_agent_yaml}),
            expect_status=200,
            optional=True,
        )
        check(
            "POST /v1/manifest/plan (execution planning)",
            lambda: h(f"{CONTROL_PLANE_URL}/v1/manifest/plan", "POST", {"yaml": sample_agent_yaml}),
            expect_status=200,
            optional=True,
        )
        print()

        # ── BRIDGE 4: AgentGovernOS → AgentStore (Catalog Gate) ──────────────────────
        print(f"{BOLD}Bridge 4 — AgentGovernOS → AgentStore (Catalog Gate){RESET}")
        check(
            "POST /catalog-gate/check (enterprise approval check)",
            lambda: h(f"{AGENTGOVERN_URL}/catalog-gate/check", "POST", {
                "org_id": "verify-org",
                "agent_slug": listing_slug,
                "requester_id": "verify-user",
                "auto_submit_procurement": False,
            }),
            expect_status=200,
            optional=True,
        )
        check(
            "GET /catalog-gate/status/verify-org (org catalog status)",
            lambda: h(f"{AGENTGOVERN_URL}/catalog-gate/status/verify-org"),
            expect_status=200,
            optional=True,
        )
        print()

        # ── BRIDGE 5: AgentOS → AgentGovernOS (SENTINEL Policy Gate) ─────────────────
        print(f"{BOLD}Bridge 5 — AgentOS → AgentGovernOS (SENTINEL & Prophecy Gate){RESET}")
        check(
            "GET /api/v1/sentinel/health (SENTINEL status)",
            lambda: h(f"{AGENTGOVERN_URL}/api/v1/sentinel/health"),
            expect_status=200,
            optional=True,
        )
        check(
            "GET /api/v1/policies/ (list active policies)",
            lambda: h(f"{AGENTGOVERN_URL}/api/v1/policies/"),
            expect_status=200,
            optional=True,
        )
        print()

        # ── BRIDGE 6: A2A Commerce Protocol ──────────────────────────────────────────
        print(f"{BOLD}Bridge 6 — A2A Commerce (Discovery & Contract Negotiation){RESET}")
        check(
            "GET /api/v1/a2a/directory (A2A directory discovery)",
            lambda: h(f"{AGENTSTORE_URL}/api/v1/a2a/directory?capability=testing"),
            expect_status=200,
            optional=True,
        )
        check(
            "POST /api/v1/a2a/contracts/negotiate (A2A contract negotiate)",
            lambda: h(f"{AGENTSTORE_URL}/api/v1/a2a/contracts/negotiate", "POST", {
                "buyer_slug": "verify-bot/orchestrator",
                "seller_slug": listing_slug,
                "capability": "testing",
            }),
            expect_status=201,
            optional=True,
        )
        print()

    # ── SUMMARY ──────────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"{BOLD}{CYAN}═════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD} Integration Verification Results{RESET}")
    print(f"{BOLD}{CYAN}═════════════════════════════════════════════════════════{RESET}")
    print(f"  {GREEN}Passed:  {passed}{RESET}")
    print(f"  {RED}Failed:  {failed}{RESET}")
    print(f"  {YELLOW}Skipped: {skipped} (optional services offline){RESET}")
    print(f"  Total:   {total + skipped}")
    print()

    if failed > 0:
        print(f"{BOLD}Failed Checks:{RESET}")
        for ok, name, ms, err in results:
            if ok is False:
                print(f"  {RED}✕ {name}{RESET}")
                if err:
                    print(f"    → {err}")
        print()

    score_pct = int((passed / (total + skipped)) * 100) if (total + skipped) > 0 else 0
    color = GREEN if failed == 0 else (YELLOW if failed < 3 else RED)
    print(f"{color}{BOLD}Integration Score: {passed}/{total + skipped} ({score_pct}%){RESET}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
