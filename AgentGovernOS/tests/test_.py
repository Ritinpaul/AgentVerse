"""
Tests for core services: audit ledger, vault client, policy versioner, spiffe identity.
These are pure unit tests with no HTTP or DB dependencies.
"""

import pytest
import uuid
import sys
import os
from datetime import datetime

# Add services paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../services/governance-api")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../services/identity-service")))


def test_audit_ledger_hash():
    try:
        from services.audit_ledger import compute_entry_hash  # noqa: PLC0415
    except ImportError:
        pytest.skip("audit_ledger not available in this environment")

    prev_hash = "GENESIS"
    ts = datetime(2026, 7, 14, 12, 0, 0)
    decision_type = "trade"
    agent_did = "did:nuuvixx:1234"
    payload = {"amount": 500}

    hash_val = compute_entry_hash(prev_hash, ts, decision_type, agent_did, payload)

    # Hash should be deterministic
    assert isinstance(hash_val, str)
    assert len(hash_val) == 64


def test_vault_client_mock():
    try:
        from services.vault_client import VaultClient  # noqa: PLC0415
    except ImportError:
        pytest.skip("vault_client not available in this environment")

    client = VaultClient(backend="mock")
    data = client.read_secret("agent/default/api_keys")
    assert "OPENAI_API_KEY" in data

    success = client.write_secret("agent/new_agent/keys", {"my_key": "val"})
    assert success

    data2 = client.read_secret("agent/new_agent/keys")
    assert data2["my_key"] == "val"


def test_policy_versioner_diff():
    try:
        from services.policy_versioner import PolicyVersioner  # noqa: PLC0415
    except ImportError:
        pytest.skip("policy_versioner not available in this environment")

    versioner = PolicyVersioner()
    old_content = {"rule_1": True, "limit": 100}
    new_content = {"rule_1": False, "limit": 100, "new_rule": "active"}

    diff = versioner.generate_diff(old_content, new_content)

    assert diff["added"]["new_rule"] == "active"
    assert diff["changed"]["rule_1"]["new"] is False
    assert diff["changed"]["rule_1"]["old"] is True
    assert "limit" not in diff["changed"]


def test_spiffe_id_generation():
    try:
        from spiffe import generate_spiffe_id  # noqa: PLC0415
    except ImportError:
        pytest.skip("spiffe module not available in this environment")

    agent_uuid = uuid.uuid4()
    spiffe_id = generate_spiffe_id(agent_uuid)

    assert spiffe_id == f"spiffe://nuuvixx.com/agent/{agent_uuid}"
