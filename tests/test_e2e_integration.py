"""
tests/test_e2e_integration.py
==============================
End-to-End System Integration Verification Suite for Nuuvixx AgentsEcosystem.

Validates the full microservice topology and all cross-plane bridges:
  - AgentStore Backend (Port 8005)
  - AgentOS Control Plane (Port 8010)
  - AgentOS Execution Plane / Interactive PTY (Port 8012)
  - AgentGovernOS SENTINEL & Catalog Gate (Port 8025)

Operates in strict mode when STRICT_INTEGRATION=1 is set (e.g. in GitHub Actions CI).
"""

import os
import sys
import json
import pytest
import httpx

AGENTSTORE_URL = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://127.0.0.1:8010")
EXECUTION_PLANE_URL = os.getenv("EXECUTION_PLANE_URL", "http://127.0.0.1:8012")
AGENTGOVERN_URL = os.getenv("AGENTGOVERN_URL", "http://127.0.0.1:8025")
NUUVIXX_API_KEY = os.getenv("NUUVIXX_API_KEY", "dev-nuuvixx-svc-key-2026")
IS_STRICT = os.getenv("STRICT_INTEGRATION", "").lower() in ("1", "true", "yes")

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-API-Key": NUUVIXX_API_KEY,
}


def _check_service_reachable(url: str) -> bool:
    try:
        r = httpx.get(f"{url}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def check_environment():
    """Ensure environment is ready or skip if services are offline outside CI."""
    store_ok = _check_service_reachable(AGENTSTORE_URL)
    govern_ok = _check_service_reachable(AGENTGOVERN_URL)
    cp_ok = _check_service_reachable(CONTROL_PLANE_URL)

    if not (store_ok or govern_ok or cp_ok):
        if IS_STRICT:
            pytest.fail(
                f"STRICT_INTEGRATION is enabled but ecosystem services are offline. "
                f"AgentStore({AGENTSTORE_URL}): {store_ok}, "
                f"GovernOS({AGENTGOVERN_URL}): {govern_ok}, "
                f"ControlPlane({CONTROL_PLANE_URL}): {cp_ok}"
            )
        else:
            pytest.skip("Ecosystem services offline and STRICT_INTEGRATION not set. Skipping E2E.")


# ── Test 1: Service Health Checks Across All Planes ──────────────────────────

def test_e2e_all_service_health(check_environment):
    """Verify HTTP /health on all ecosystem microservices."""
    endpoints = [
        ("AgentStore", f"{AGENTSTORE_URL}/health"),
        ("AgentOS Control Plane", f"{CONTROL_PLANE_URL}/health"),
        ("AgentOS Execution Plane", f"{EXECUTION_PLANE_URL}/health"),
        ("AgentGovernOS API", f"{AGENTGOVERN_URL}/health"),
    ]

    with httpx.Client(timeout=5.0) as client:
        for name, url in endpoints:
            resp = client.get(url)
            assert resp.status_code == 200, f"{name} health check failed: {resp.status_code}"
            data = resp.json()
            assert "status" in data or "healthy" in str(data).lower() or data.get("service")


# ── Test 2: AgentStore Template & Catalog Bridge ─────────────────────────────

def test_e2e_agentstore_template_and_agent_registry(check_environment):
    """Verify Bridge 1: Dynamic template listing and agent manifest publish pipeline."""
    with httpx.Client(timeout=5.0) as client:
        # Dynamic template catalog
        tpl_res = client.get(f"{AGENTSTORE_URL}/api/v1/registry/templates", headers=HEADERS)
        assert tpl_res.status_code == 200
        templates = tpl_res.json()
        assert isinstance(templates, list)
        assert len(templates) > 0

        # Publish an agent manifest
        manifest_payload = {
            "builder_id": "ci-e2e-runner",
            "agent_yaml": """
name: ci-e2e-verification-agent
version: 1.0.0
description: End-to-end integration test agent
framework: custom
model:
  provider: openai
  name: gpt-4o-mini
tools:
  - type: mcp
    server: echo
    tool: echo
""",
            "category": "developer-tools",
        }

        pub_res = client.post(
            f"{AGENTSTORE_URL}/api/v1/registry/agents",
            json=manifest_payload,
            headers=HEADERS,
        )
        assert pub_res.status_code in (200, 201)
        pub_data = pub_res.json()
        assert "slug" in pub_data or "id" in pub_data

        listing_slug = pub_data.get("slug", "ci-e2e-runner/ci-e2e-verification-agent")

        # Bridge 2: Query CLI execution manifest
        cli_res = client.get(
            f"{AGENTSTORE_URL}/api/v1/cli/run/{listing_slug}",
            headers=HEADERS,
        )
        if cli_res.status_code == 200:
            manifest = cli_res.json()
            assert "listing_id" in manifest or "slug" in manifest or "trust_score" in manifest


# ── Test 3: AgentOS Control Plane Manifest Lifecycle ─────────────────────────

def test_e2e_agentos_control_plane_lifecycle(check_environment):
    """Verify AgentOS Control Plane manifest validation and plan endpoints."""
    sample_yaml = """
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: ci-e2e-agent
  version: 1.0.0
model:
  provider: openai
  name: gpt-4o-mini
"""
    with httpx.Client(timeout=5.0) as client:
        # Validate manifest
        val_res = client.post(
            f"{CONTROL_PLANE_URL}/v1/manifest/validate",
            json={"yaml": sample_yaml},
            headers=HEADERS,
        )
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data.get("valid") is True or "errors" in val_data

        # Plan run
        plan_res = client.post(
            f"{CONTROL_PLANE_URL}/v1/manifest/plan",
            json={"yaml": sample_yaml},
            headers=HEADERS,
        )
        assert plan_res.status_code == 200
        plan_data = plan_res.json()
        assert "canonicalHash" in plan_data or "plan" in plan_data or plan_data.get("valid") is True


# ── Test 4: AgentGovernOS SENTINEL & Prophecy Engine ─────────────────────────

def test_e2e_governos_sentinel_policy_and_prophecy(check_environment):
    """Verify Bridge 5: Pre-execution policy evaluation and Prophecy engine."""
    with httpx.Client(timeout=5.0) as client:
        # Check Sentinel health
        health_res = client.get(
            f"{AGENTGOVERN_URL}/api/v1/sentinel/health",
            headers=HEADERS,
        )
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data.get("service") == "SENTINEL"
        assert health_data.get("prophecy_engine") == "ready"

        # List active policies
        policies_res = client.get(
            f"{AGENTGOVERN_URL}/api/v1/policies/",
            headers=HEADERS,
        )
        assert policies_res.status_code == 200
        policies = policies_res.json()
        assert isinstance(policies, list)


# ── Test 5: AgentGovernOS Catalog Gate (Bridge 4) ─────────────────────────────

def test_e2e_governos_catalog_gate(check_environment):
    """Verify Bridge 4: Catalog Gate organization compliance check."""
    with httpx.Client(timeout=5.0) as client:
        gate_res = client.post(
            f"{AGENTGOVERN_URL}/catalog-gate/check",
            json={
                "org_id": "ci-org-test",
                "agent_slug": "nuuvixx/support-agent",
                "requester_id": "ci-runner",
                "auto_submit_procurement": False,
            },
            headers=HEADERS,
        )
        assert gate_res.status_code == 200
        gate_data = gate_res.json()
        assert "allowed" in gate_data
        assert "reason" in gate_data
