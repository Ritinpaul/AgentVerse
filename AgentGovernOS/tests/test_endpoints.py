# pyre-ignore-all-errors
"""
Integration tests for routers: GENESIS (agents/dna), PULSE (trust), SENTINEL (policies).

Uses the shared `api_client` fixture from conftest.py which bootstraps
the FastAPI app against an in-memory SQLite DB.

Covers:
  ✅ GENESIS — CRUD, DNA, lineage, bulk import
  ✅ PULSE   — trust score, events, history, velocity, leaderboard, promotion eligibility
  ✅ SENTINEL — evaluate, simulate (dry-run), health, policy CRUD
"""
# conftest.py already adds service roots to sys.path before this module is collected.

import pytest
from uuid import uuid4

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _agent_payload(*, agent_code=None, tier="T3", authority_limit=5000.0):
    """Minimal valid agent registration payload."""
    return {
        "agent_code": agent_code or f"AG-{uuid4().hex[:6].upper()}",
        "display_name": "Test Agent",
        "role": "analyst",
        "crewai_role": "Analyst",
        "crewai_backstory": "A test backstory",
        "tier": tier,
        "authority_limit": authority_limit,
        "dna_profile": {"compliance_threshold": 0.8, "caution_factor": 0.5},
        "platform_bindings": [],
    }


def _create_agent(client, *, agent_code=None, tier="T3", authority_limit=5000.0):
    """Register a minimal agent and return the full response dict."""
    resp = client.post("/api/v1/agents/", json=_agent_payload(
        agent_code=agent_code, tier=tier, authority_limit=authority_limit
    ))
    assert resp.status_code == 201, f"Agent creation failed: {resp.text}"
    return resp.json()


def _action_payload(agent_id, *, amount=100.0, action_type="purchase"):
    """Sentinel-compatible evaluate/simulate payload."""
    return {
        "agent_id": agent_id,
        "action": {"type": action_type, "amount": amount},
        "context": {"requestor": "test-suite"},
    }


def _policy_payload(*, name=None, max_amount=10000, applies_to_tiers=None):
    """Minimal policy creation payload."""
    return {
        "policy_code": name or f"POL-{uuid4().hex[:6].upper}",
        "policy_name": name or f"Test Policy {uuid4().hex[:4]}",
        "description": "Test policy",
        "rule_definition": {"type": "spending_limit", "max_amount": max_amount},
        "applies_to_roles": ["*"],
        "applies_to_tiers": applies_to_tiers or ["T4", "T3", "T2", "T1"],
        "severity": "medium",
        "action_on_violation": "escalate",
    }


# ══════════════════════════════════════════════════════════════
# GENESIS  (/api/v1/agents)
# ══════════════════════════════════════════════════════════════

class TestGenesisRegister:
    def test_register_agent_success(self, api_client):
        agent = _create_agent(api_client)
        assert "id" in agent
        assert agent["status"] == "active"

    def test_register_duplicate_returns_409(self, api_client):
        code = f"DUP-{uuid4().hex[:4].upper}"
        _create_agent(api_client, agent_code=code)
        resp = api_client.post("/api/v1/agents/", json=_agent_payload(agent_code=code))
        assert resp.status_code == 409

    def test_list_agents(self, api_client):
        _create_agent(api_client)
        resp = api_client.get("/api/v1/agents/")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert data["total"] >= 1

    def test_get_agent_by_id(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/agents/{agent['id']}")
        assert resp.status_code == 200
        assert resp.json()["agent_code"] == agent["agent_code"]

    def test_get_agent_not_found(self, api_client):
        resp = api_client.get(f"/api/v1/agents/{uuid4()}")
        assert resp.status_code == 404

    def test_retire_agent(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.delete(f"/api/v1/agents/{agent['id']}")
        assert resp.status_code == 204
        fetched = api_client.get(f"/api/v1/agents/{agent['id']}")
        assert fetched.json["status"] == "retired"


class TestGenesisDNA:
    def test_get_dna_returns_profile(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/agents/{agent['id']}/dna")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_code"] == agent["agent_code"]
        assert "dna_profile" in data
        assert isinstance(data["genes"], list)

    def test_mutate_creates_new_trait(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.post(
            f"/api/v1/agents/{agent['id']}/dna/mutate",
            json={"trait": "risk_appetite", "delta": 0.1, "reason": "Q1 review"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trait_mutated"] == "risk_appetite"
        # New trait initialises at 0.5 + delta = 0.6
        assert abs(data["new_value"] - 0.6) < 0.001

    def test_mutate_existing_trait(self, api_client):
        agent = _create_agent(api_client)
        # compliance_threshold starts at 0.8 – bump it by 0.05
        resp = api_client.post(
            f"/api/v1/agents/{agent['id']}/dna/mutate",
            json={"trait": "compliance_threshold", "delta": 0.05, "reason": "Reward"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert abs(data["new_value"] - 0.85) < 0.001

    def test_mutate_delta_out_of_range_422(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.post(
            f"/api/v1/agents/{agent['id']}/dna/mutate",
            json={"trait": "x", "delta": 5.0, "reason": "bad"},  # >1.0
        )
        assert resp.status_code == 422

    def test_mutate_agent_not_found(self, api_client):
        resp = api_client.post(
            f"/api/v1/agents/{uuid4()}/dna/mutate",
            json={"trait": "x", "delta": 0.1, "reason": "test"},
        )
        assert resp.status_code == 404

    def test_lineage_root_only(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/agents/{agent['id']}/lineage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["root"]["id"] == agent["id"]
        assert data["ancestors"] == []
        assert data["descendants"] == []
        assert data["total_nodes"] == 1


class TestGenesisBulkImport:
    """Tests for POST /api/v1/agents/import — bulk manifest import."""

    def test_bulk_import_creates_agents(self, api_client):
        codes = [f"BULK-{uuid4().hex[:4].upper}" for _ in range(3)]
        resp = api_client.post(
            "/api/v1/agents/import",
            json={
                "agents": [
                    {"agent_code": c, "display_name": f"Agent {c}", "tier": "T4"}
                    for c in codes
                ],
                "skip_duplicates": True,
            },
        )
        assert resp.status_code == 207, resp.text
        data = resp.json()
        assert data["summary"]["created"] == 3
        assert data["summary"]["errors"] == 0
        # All returned results should have IDs
        created = [r for r in data["results"] if r["status"] == "created"]
        assert all("id" in r for r in created)

    def test_bulk_import_skips_duplicates(self, api_client):
        code = f"SKIP-{uuid4().hex[:4].upper}"
        # Pre-create the agent
        _create_agent(api_client, agent_code=code)
        # Import should skip it
        resp = api_client.post(
            "/api/v1/agents/import",
            json={
                "agents": [{"agent_code": code, "tier": "T3"}],
                "skip_duplicates": True,
            },
        )
        assert resp.status_code == 207
        data = resp.json()
        assert data["summary"]["skipped"] == 1
        assert data["summary"]["created"] == 0

    def test_bulk_import_errors_on_missing_code(self, api_client):
        resp = api_client.post(
            "/api/v1/agents/import",
            json={
                "agents": [{"display_name": "No Code Agent", "tier": "T4"}],
                "skip_duplicates": True,
            },
        )
        assert resp.status_code == 207
        data = resp.json()
        assert data["summary"]["errors"] == 1

    def test_bulk_import_mixed_results(self, api_client):
        existing_code = f"EX-{uuid4().hex[:4].upper}"
        new_code = f"NW-{uuid4().hex[:4].upper}"
        _create_agent(api_client, agent_code=existing_code)

        resp = api_client.post(
            "/api/v1/agents/import",
            json={
                "agents": [
                    {"agent_code": existing_code, "tier": "T3"},
                    {"agent_code": new_code, "tier": "T4"},
                    {"display_name": "Missing code"},  # error
                ],
                "skip_duplicates": True,
            },
        )
        assert resp.status_code == 207
        s = resp.json()["summary"]
        assert s["created"] == 1
        assert s["skipped"] == 1
        assert s["errors"] == 1


# ══════════════════════════════════════════════════════════════
# PULSE  (/api/v1/trust)
# ══════════════════════════════════════════════════════════════

class TestPulseTrust:
    def test_trust_score_for_existing_agent(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/trust/{agent['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert "trust_score" in data
        assert 0.0 <= data["trust_score"] <= 1.0

    def test_trust_score_unknown_agent_404(self, api_client):
        resp = api_client.get(f"/api/v1/trust/{uuid4()}")
        assert resp.status_code == 404

    def test_record_trust_event(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.post(
            "/api/v1/trust/event",
            json={
                "agent_id": agent["id"],
                "event_type": "decision_success_simple",
                "description": "Routine approval processed correctly",
                "metadata": {},
            },
        )
        assert resp.status_code in (200, 201), resp.text

    def test_trust_history(self, api_client):
        agent = _create_agent(api_client)
        api_client.post(
            "/api/v1/trust/event",
            json={
                "agent_id": agent["id"],
                "event_type": "decision_success_simple",
                "description": "Test event",
                "metadata": {},
            },
        )
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/history")
        assert resp.status_code == 200
        history = resp.json()
        assert isinstance(history, (list, dict))

    def test_leaderboard_returns_list(self, api_client):
        resp = api_client.get("/api/v1/trust/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_promotion_eligibility(self, api_client):
        agent = _create_agent(api_client, tier="T3")
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/promotion-eligibility")
        assert resp.status_code == 200
        data = resp.json()
        assert "eligible" in data


class TestPulseVelocity:
    """Tests for the new GET /api/v1/trust/{agent_id}/velocity endpoint."""

    def test_velocity_returns_correctly_structured_response(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/velocity")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Required top-level keys
        required = {
            "agent_code", "current_score", "current_tier",
            "velocity_7d", "velocity_14d", "velocity_30d",
            "acceleration", "trend", "events_last_7d",
            "positive_streak", "negative_streak",
            "projected_score_30d", "projected_tier_30d",
            "projection_note",
        }
        for key in required:
            assert key in data, f"Missing key: {key}"

    def test_velocity_reflects_recent_positive_events(self, api_client):
        agent = _create_agent(api_client)
        # Fire 3 positive events
        for _ in range(3):
            api_client.post(
                "/api/v1/trust/event",
                json={
                    "agent_id": agent["id"],
                    "event_type": "decision_success_complex",
                    "description": "High-value decision executed correctly",
                    "metadata": {},
                },
            )
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/velocity")
        assert resp.status_code == 200
        data = resp.json()
        # After positive events, velocity_7d should be >= 0
        assert data["velocity_7d"] >= 0.0
        # Positive streak should be >= 1
        assert data["positive_streak"] >= 1

    def test_velocity_trend_labels_are_valid(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/velocity")
        assert resp.status_code == 200
        assert resp.json()["trend"] in ("rising", "falling", "stable")

    def test_velocity_projected_score_is_bounded(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/velocity")
        assert resp.status_code == 200
        score = resp.json()["projected_score_30d"]
        assert 0.0 <= score <= 1.0

    def test_velocity_projected_tier_is_valid_tier(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/velocity")
        assert resp.status_code == 200
        tier = resp.json()["projected_tier_30d"]
        assert tier.startswith("T")

    def test_velocity_unknown_agent_returns_404(self, api_client):
        resp = api_client.get(f"/api/v1/trust/{uuid4()}/velocity")
        assert resp.status_code == 404

    def test_velocity_projection_note_contains_agent_code(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.get(f"/api/v1/trust/{agent['id']}/velocity")
        assert resp.status_code == 200
        note = resp.json()["projection_note"]
        assert agent["agent_code"] in note


# ══════════════════════════════════════════════════════════════
# SENTINEL  (/api/v1/sentinel  +  /api/v1/policies)
# ══════════════════════════════════════════════════════════════

class TestSentinelPolicies:
    def _create_policy(self, client, *, name=None, max_amount=10000):
        resp = client.post("/api/v1/policies/", json=_policy_payload(
            name=name, max_amount=max_amount
        ))
        assert resp.status_code in (200, 201), f"Policy creation failed: {resp.text}"
        return resp.json()

    def test_create_policy(self, api_client):
        policy = self._create_policy(api_client)
        assert "id" in policy

    def test_list_policies(self, api_client):
        self._create_policy(api_client)
        resp = api_client.get("/api/v1/policies/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_update_policy(self, api_client):
        policy = self._create_policy(api_client)
        resp = api_client.patch(
            f"/api/v1/policies/{policy['id']}",
            json={"description": "Updated description"},
        )
        assert resp.status_code == 200

    def test_deactivate_policy(self, api_client):
        policy = self._create_policy(api_client)
        resp = api_client.delete(f"/api/v1/policies/{policy['id']}")
        assert resp.status_code in (200, 204)


class TestSentinelEvaluate:
    def test_evaluate_approved_action(self, api_client):
        agent = _create_agent(api_client, tier="T2", authority_limit=50000.0)
        resp = api_client.post(
            "/api/v1/sentinel/evaluate",
            json=_action_payload(agent["id"], amount=100.0),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["verdict"] in ("APPROVED", "ESCALATE", "BLOCKED", "REQUIRES_REVIEW",
                                   "approve", "escalate", "block")

    def test_evaluate_unknown_agent_404(self, api_client):
        resp = api_client.post(
            "/api/v1/sentinel/evaluate",
            json=_action_payload(str(uuid4()), amount=50.0),
        )
        assert resp.status_code == 404

    def test_evaluate_over_authority_limit_not_approved(self, api_client):
        # Authority limit is 5000, request 10M
        agent = _create_agent(api_client, tier="T4", authority_limit=5000.0)
        resp = api_client.post(
            "/api/v1/sentinel/evaluate",
            json=_action_payload(agent["id"], amount=9_999_999.0),
        )
        assert resp.status_code == 200
        # Must NOT be blindly approved
        verdict = resp.json()["verdict"]
        assert verdict not in ("APPROVED", "approve")

    def test_evaluate_includes_policy_results(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.post(
            "/api/v1/sentinel/evaluate",
            json=_action_payload(agent["id"], amount=100.0),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "policy_results" in data
        assert isinstance(data["policy_results"], list)

    def test_evaluate_includes_confidence_score(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.post(
            "/api/v1/sentinel/evaluate",
            json=_action_payload(agent["id"], amount=100.0),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0


class TestSentinelSimulate:
    """Tests for the new POST /api/v1/sentinel/simulate endpoint."""

    def test_simulate_returns_verdict(self, api_client):
        agent = _create_agent(api_client, tier="T2", authority_limit=50000.0)
        resp = api_client.post(
            "/api/v1/sentinel/simulate",
            json=_action_payload(agent["id"], amount=100.0),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "verdict" in data
        assert "reasoning" in data

    def test_simulate_unknown_agent_404(self, api_client):
        resp = api_client.post(
            "/api/v1/sentinel/simulate",
            json=_action_payload(str(uuid4())),
        )
        assert resp.status_code == 404

    def test_simulate_reasoning_contains_dry_run_marker(self, api_client):
        agent = _create_agent(api_client, tier="T2", authority_limit=50000.0)
        resp = api_client.post(
            "/api/v1/sentinel/simulate",
            json=_action_payload(agent["id"], amount=100.0),
        )
        assert resp.status_code == 200
        reasoning = resp.json()["reasoning"]
        # Dry-run should be marked in the reasoning
        assert "[DRY-RUN]" in reasoning

    def test_simulate_does_not_write_decision(self, api_client):
        """Simulate should not increase the agent's decision count."""
        agent = _create_agent(api_client)
        # Get initial total_decisions
        initial = api_client.get(f"/api/v1/agents/{agent['id']}").json
        initial_count = initial.get("total_decisions", 0)

        # Run simulate multiple times
        for _ in range(3):
            api_client.post(
                "/api/v1/sentinel/simulate",
                json=_action_payload(agent["id"], amount=100.0),
            )

        # Check that decision count did NOT increase
        after = api_client.get(f"/api/v1/agents/{agent['id']}").json
        assert after.get("total_decisions", 0) == initial_count

    def test_simulate_over_limit_gives_escalate_verdict(self, api_client):
        agent = _create_agent(api_client, tier="T4", authority_limit=5000.0)
        resp = api_client.post(
            "/api/v1/sentinel/simulate",
            json=_action_payload(agent["id"], amount=999_999.0),
        )
        assert resp.status_code == 200
        verdict = resp.json()["verdict"]
        assert verdict not in ("APPROVED", "approve")

    def test_simulate_includes_policy_results(self, api_client):
        agent = _create_agent(api_client)
        resp = api_client.post(
            "/api/v1/sentinel/simulate",
            json=_action_payload(agent["id"], amount=100.0),
        )
        assert resp.status_code == 200
        assert "policy_results" in resp.json()


class TestSentinelHealth:
    """Tests for the new GET /api/v1/sentinel/health endpoint."""

    def test_health_returns_healthy(self, api_client):
        resp = api_client.get("/api/v1/sentinel/health")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "SENTINEL"

    def test_health_includes_active_policy_count(self, api_client):
        resp = api_client.get("/api/v1/sentinel/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_policies" in data
        assert isinstance(data["active_policies"], int)

    def test_health_includes_checked_at_timestamp(self, api_client):
        resp = api_client.get("/api/v1/sentinel/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "checked_at" in data
        # Should be ISO-format timestamp
        from datetime import datetime
        datetime.fromisoformat(data["checked_at"].replace("Z", "+00:00"))
