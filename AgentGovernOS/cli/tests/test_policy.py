import pytest
from agentgovern.policy.engine import run_policy_checks, PolicyCheckResult
from agentgovern.scanner.manifest import AgentDefinition

def test_default_policy_passes:
    agents = [
        AgentDefinition(
            code="A-001",
            name="Good Bot",
            framework="crewai",
            tier="T1",
            authority_limit=100.0,
            allowed_actions=["read"],
        )
    ]
    # default bundle
    result = run_policy_checks(agents, None, bundle_name="default")
    assert result.passed
    assert len(result.violations) == 0

def test_default_policy_fails_wildcard:
    agents = [
        AgentDefinition(
            code="A-002",
            name="Bad Bot",
            framework="crewai",
            tier="T1",
            authority_limit=100.0,
            allowed_actions=["*"],
        )
    ]
    result = run_policy_checks(agents, None, bundle_name="default")
    assert not result.passed
    assert any(v.rule_id == "AG-004" for v in result.violations)

def test_enterprise_policy_fails_missing_denied:
    agents = [
        AgentDefinition(
            code="A-003",
            name="No Deny Bot",
            framework="crewai",
            tier="T1",
            authority_limit=100.0,
            denied_actions=[],
        )
    ]
    result = run_policy_checks(agents, None, bundle_name="enterprise")
    # enterprise bundle checks denied actions
    assert any(v.rule_id == "AG-E02" for v in result.violations)
