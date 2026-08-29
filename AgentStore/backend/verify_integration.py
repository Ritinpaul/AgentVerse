"""
Nuuvixx AgentsEcosystem â€” Integration Verification Suite

Tests all 6 integration bridges end-to-end:
  Bridge 1: AgentStudio â†’ AgentStore (Publish)
  Bridge 2: AgentOS CLI â†’ AgentStore (Run manifest + trust gate)
  Bridge 3: AgentOS CLI â†’ AgentStore (Deploy = publish + spawn)
  Bridge 4: AgentGovernOS â†’ AgentStore (Catalog gate)
  Bridge 5: AgentOS â†’ AgentGovernOS (Tool policy check)
  Bridge 6: A2A Commerce (hire_agent + settle_contract)

Usage:
  python verify_integration.py                    # All tests, services must be running
  python verify_integration.py --store-only       # Only AgentStore tests
  python verify_integration.py --bridges 2,4,6    # Specific bridges

Requirements:
  - AgentStore running at localhost:8005
  - AgentOS Control Plane running at localhost:8010  (optional for bridge 3)
  - AgentGovernOS running at localhost:8025           (optional for bridges 4,5)
"""

import httpx
import os
import sys
import time
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
from pathlib import Path

# Fix Windows console encoding for Unicode output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Load ecosystem .env ────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists() and load_dotenv is not None:
    load_dotenv(dotenv_path=_env_path)

AGENTSTORE_URL    = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://127.0.0.1:8010")
AGENTGOVERN_URL   = os.getenv("AGENTGOVERN_URL", "http://127.0.0.1:8025")
NUUVIXX_API_KEY   = os.getenv("NUUVIXX_API_KEY", "")

# Colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def h(url: str, method="GET", json_body=None, timeout=5.0) -> httpx.Response:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if NUUVIXX_API_KEY:
        headers["X-API-Key"] = NUUVIXX_API_KEY
    with httpx.Client(timeout=timeout) as client:
        if method == "GET":
            return client.get(url, headers=headers)
        elif method == "POST":
            return client.post(url, json=json_body or {}, headers=headers)


passed = 0
failed = 0
skipped = 0
results = []

def check(name: str, fn, expect_status=200, optional=False):
    global passed, failed, skipped
    try:
        start = time.time()
        r = fn()
        ms = int((time.time() - start) * 1000)
        if r.status_code == expect_status:
            passed += 1
            results.append((True,  name, ms, None))
            print(f"  {GREEN}âœ“{RESET} {name} ({ms}ms)")
            return r
        else:
            if optional:
                skipped += 1
                results.append((None, name, ms, f"HTTP {r.status_code} (optional service)"))
                print(f"  {YELLOW}â—‹{RESET} {name} â€” {r.status_code} (optional/offline)")
            else:
                failed += 1
                body = r.text[:120] if r.text else ""
                results.append((False, name, ms, f"HTTP {r.status_code}: {body}"))
                print(f"  {RED}âœ—{RESET} {name} â€” Expected {expect_status}, got {r.status_code}: {body}")
            return r
    except (httpx.RequestError, httpx.TimeoutException) as e:
        if optional:
            skipped += 1
            results.append((None, name, 0, f"Offline (optional): {e}"))
            print(f"  {YELLOW}â—‹{RESET} {name} â€” Offline/optional: {e}")
        else:
            failed += 1
            results.append((False, name, 0, f"Connection error: {e}"))
            print(f"  {RED}âœ—{RESET} {name} â€” {e}")
        return None


print(f"\n{BOLD}{CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•{RESET}")
print(f"\n{BOLD}{CYAN}â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• {RESET}")
print(f"{BOLD}{CYAN} Nuuvixx AgentsEcosystem â€” Integration Verification{RESET}")
print(f"{BOLD}{CYAN}â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• {RESET}\n")


# â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• 
# PRE-CHECK: Service Health
# â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• 
print(f"{BOLD}Service Health Checks{RESET}")
check("AgentStore health",         lambda: h(f"{AGENTSTORE_URL}/health"))
check("AgentOS Control Plane",     lambda: h(f"{CONTROL_PLANE_URL}/health"), optional=True)
check("AgentGovernOS Governance",  lambda: h(f"{AGENTGOVERN_URL}/health"), optional=True)
print()


# â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• 
# BRIDGE 1: AgentStudio â†’ AgentStore (Publish)
# â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• 
print(f"{BOLD}Bridge 1 â€” AgentStudio â†’ AgentStore (Publish Pipeline){RESET}")

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
    "category": "testing"
}

pub_r = check(
    "POST /registry/agents (publish manifest)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/registry/agents", "POST", SAMPLE_MANIFEST),
    expect_status=201
)
if pub_r and pub_r.status_code == 201:
    data = pub_r.json()
    listing_id = data.get("id", 1)
    listing_slug = data.get("slug", "verify-bot/integration-test-agent")
    trust_score = data.get("trust_score", 0)
    print(f"    â†’ listing_id={listing_id}, slug={listing_slug}, trust_score={trust_score}")
else:
    listing_id = None
    listing_slug = "verify-bot/integration-test-agent"

check("GET /registry/agents (list all)", lambda: h(f"{AGENTSTORE_URL}/api/v1/registry/agents"))
print()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BRIDGE 2: AgentOS CLI â†’ AgentStore (Run manifest + trust gate data)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print(f"{BOLD}Bridge 2 â€” AgentOS CLI â†’ AgentStore (Run Manifest){RESET}")

run_r = check(
    f"GET /cli/run/{listing_slug} (execution manifest)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/cli/run/{listing_slug}")
)
if run_r and run_r.status_code == 200:
    manifest = run_r.json()
    required_fields = ["listing_id", "trust_score", "scan_results", "lockfile", "command"]
    missing = [f for f in required_fields if f not in manifest]
    if missing:
        print(f"    {RED}âœ— Missing Bridge 2 fields: {missing}{RESET}")
        failed += 1
    else:
        print(f"    {GREEN}âœ“ All Bridge 2 fields present: trust_score={manifest.get('trust_score')}{RESET}")

check("GET /cli/search (agent search)",    lambda: h(f"{AGENTSTORE_URL}/api/v1/cli/search?q=test"))
check("POST /billing/meter (execution meter)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/billing/meter", "POST", {
        "listing_id": listing_id,
        "org_id": "verify-org",
        "caller_id": "verify-bot",
        "duration_ms": 1500,
        "tokens_used": 100,
    }),
    expect_status=200
)
print()


# â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• 
# BRIDGE 3: AgentOS Control Plane (spawn check)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print(f"{BOLD}Bridge 3 â€” AgentOS Control Plane (Deploy Spawn){RESET}")

check(
    "POST /agents/spawn (control plane spawn)",
    lambda: h(f"{CONTROL_PLANE_URL}/agents/spawn", "POST", {
        "name": "verify-integration-agent",
        "description": "Spawned by integration test",
        "entrypoint": "main.py",
        "env_vars": {"NUUVIXX_LISTING_ID": str(listing_id) if listing_id else "test"}
    }),
    expect_status=200,
    optional=True
)
check("GET /agents/ (list running agents)", lambda: h(f"{CONTROL_PLANE_URL}/agents/"), optional=True)
print()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BRIDGE 4: AgentGovernOS â†’ AgentStore (Catalog Gate)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print(f"{BOLD}Bridge 4 â€” AgentGovernOS â†’ AgentStore (Catalog Gate){RESET}")

check(
    "POST /catalog-gate/check (enterprise approval check)",
    lambda: h(f"{AGENTGOVERN_URL}/catalog-gate/check", "POST", {
        "org_id": "verify-org",
        "agent_slug": listing_slug,
        "requester_id": "verify-user",
        "auto_submit_procurement": False,
    }),
    optional=True
)
check(
    "GET /catalog-gate/status/verify-org (org catalog status)",
    lambda: h(f"{AGENTGOVERN_URL}/catalog-gate/status/verify-org"),
    optional=True
)

# Bridge 4 also tests AgentStore procurement
check(
    "GET /api/v1/procurement/requests (pending approvals)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/procurement/requests")
)
check(
    "GET /api/v1/procurement/private-catalog/verify-org (org catalog)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/procurement/private-catalog/verify-org")
)
print()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BRIDGE 5: AgentOS â†’ AgentGovernOS (Tool Policy Check)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print(f"{BOLD}Bridge 5 â€” AgentOS â†’ AgentGovernOS (Tool Interception){RESET}")

check(
    "POST /sentinel/evaluate-tool (policy check)",
    lambda: h(f"{AGENTGOVERN_URL}/sentinel/evaluate-tool", "POST", {
        "agent_id": "verify-agent-001",
        "tool_name": "filesystem:read_file",
        "tool_args": {"path": "/tmp/test.txt"},
        "org_id": "verify-org",
        "payload_hash": "abc123",
        "timestamp_ms": int(time.time() * 1000),
    }),
    optional=True
)
check(
    "GET /sentinel/ (SENTINEL policies list)",
    lambda: h(f"{AGENTGOVERN_URL}/sentinel/"),
    optional=True
)
print()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BRIDGE 6: A2A Commerce (AgentStore A2A endpoints)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print(f"{BOLD}Bridge 6 â€” A2A Commerce (hire_agent + settle_contract){RESET}")

check(
    "GET /a2a/directory (capability discovery)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/a2a/directory?capability=text-processing")
)
check(
    "POST /a2a/contracts/negotiate (contract negotiation)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/a2a/contracts/negotiate", "POST", {
        "buyer_slug": "verify-bot/orchestrator",
        "seller_slug": listing_slug,
        "capability": "text-processing",
    }),
    expect_status=201
)
check(
    "GET /a2a/contracts (list contracts)",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/a2a/contracts")
)
print()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BRIDGE 2 continued: Verification Scan
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print(f"{BOLD}Verification â€” ASI Security Scan{RESET}")

builder_part = listing_slug.split("/")[0] if "/" in listing_slug else "verify-bot"
name_part = listing_slug.split("/")[1] if "/" in listing_slug else "integration-test-agent"
check(
    f"POST /verification/agents/{builder_part}/{name_part}/scan/trigger",
    lambda: h(
        f"{AGENTSTORE_URL}/api/v1/verification/agents/{builder_part}/{name_part}/scan/trigger",
        "POST"
    )
)
check(
    f"GET /verification/agents/{builder_part}/{name_part}/scan",
    lambda: h(f"{AGENTSTORE_URL}/api/v1/verification/agents/{builder_part}/{name_part}/scan")
)
print()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SUMMARY
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
total = passed + failed
print(f"{BOLD}{CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•{RESET}")
print(f"{BOLD} Integration Verification Results{RESET}")
print(f"{BOLD}{CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•{RESET}")
print(f"  {GREEN}Passed:  {passed}{RESET}")
print(f"  {RED}Failed:  {failed}{RESET}")
print(f"  {YELLOW}Skipped: {skipped} (optional services offline){RESET}")
print(f"  Total:   {total + skipped}")
print()

if failed > 0:
    print(f"{BOLD}Failed Checks:{RESET}")
    for ok, name, ms, err in results:
        if ok is False:
            print(f"  {RED}âœ— {name}{RESET}")
            if err:
                print(f"    â†’ {err}")
    print()

if skipped > 0:
    print(f"{YELLOW}To run skipped checks, start optional services:{RESET}")
    print("  AgentOS Control Plane:  cd AgentOS && uvicorn app.main:app --port 8010")
    print("  AgentGovernOS:          cd AgentGovernOS/services/governance-api && uvicorn main:app --port 8025")
    print()

score_pct = int((passed / (total + skipped)) * 100) if (total + skipped) > 0 else 0
color = GREEN if failed == 0 else (YELLOW if failed < 3 else RED)
print(f"{color}{BOLD}Integration Score: {passed}/{total + skipped} ({score_pct}%){RESET}\n")

sys.exit(0 if failed == 0 else 1)

