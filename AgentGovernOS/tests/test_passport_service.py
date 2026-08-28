"""
Tests: Agent Passport Service

Covers:
  - Passport creation: field defaults, authority limit from tier
  - Invalid environment raises ValueError
  - Expired passport detection
  - DNA fingerprint: deterministic, different genes → different hash
  - JWT issue: valid token, correct claims, ag namespace
  - JWT verify: succeeds on valid token
  - JWT verify: raises on expired token
  - JWT verify: raises on tampered token
  - JWT verify: raises on revoked JTI
  - Revoke: JTI added to revocation set
  - Rotate: old revoked, new token issued
  - Rotate: new token verifiable after rotation
  - Environment permission check
  - is_valid property
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "identity-service"))

import pytest
import jwt
from datetime import datetime, timezone, timedelta
from passport import AgentPassport, PassportService, compute_dna_fingerprint, TIER_AUTHORITY_LIMITS


SECRET = "test-secret-key-for-unit-tests"


def make_service(**kwargs) -> PassportService:
    return PassportService(private_key=SECRET, public_key=SECRET, algorithm="HS256", **kwargs)


def make_passport(**kwargs) -> AgentPassport:
    defaults = dict(
        agent_id="agent-001",
        agent_name="DisputeResolver",
        agent_role="dispute_resolver",
        tier="T2",
        trust_score=0.78,
        allowed_environments=["cloud", "edge"],
        dna_fingerprint="abc123",
    )
    defaults.update(kwargs)
    return AgentPassport(**defaults)


class TestAgentPassport:
    def test_authority_limit_derived_from_tier(self):
        p = make_passport(tier="T1")
        assert p.authority_limit == TIER_AUTHORITY_LIMITS["T1"]

    def test_t4_authority_limit_is_zero(self):
        p = make_passport(tier="T4")
        assert p.authority_limit == 0

    def test_expires_24h_by_default(self):
        p = make_passport
        delta = (p.expires_at - p.issued_at).total_seconds
        assert 86390 <= delta <= 86410   # ~24 hours

    def test_invalid_environment_raises(self):
        with pytest.raises(ValueError, match="Invalid environments"):
            make_passport(allowed_environments=["mars", "jupiter"])

    def test_is_valid_on_fresh_passport(self):
        p = make_passport
        assert p.is_valid is True

    def test_is_expired_on_stale(self):
        p = make_passport
        p.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        assert p.is_expired is True
        assert p.is_valid is False

    def test_is_valid_false_when_revoked(self):
        p = make_passport
        p.revoked = True
        assert p.is_valid is False

    def test_allows_environment_true(self):
        p = make_passport(allowed_environments=["cloud", "edge"])
        assert p.allows_environment("cloud") is True
        assert p.allows_environment("edge") is True

    def test_allows_environment_false(self):
        p = make_passport(allowed_environments=["cloud"])
        assert p.allows_environment("client") is False


class TestDNAFingerprint:
    def test_fingerprint_is_64_chars(self):
        h = compute_dna_fingerprint([{"gene_name": "risk:heuristic", "gene_type": "risk_heuristic", "strength": 0.75}])
        assert len(h) == 64

    def test_empty_genes_gives_constant(self):
        h = compute_dna_fingerprint([])
        assert len(h) == 64

    def test_deterministic_same_genes(self):
        genes = [{"gene_name": "test", "gene_type": "risk_heuristic", "strength": 0.75}]
        h1 = compute_dna_fingerprint(genes)
        h2 = compute_dna_fingerprint(genes)
        assert h1 == h2

    def test_different_genes_different_hash(self):
        g1 = [{"gene_name": "gene_a", "gene_type": "risk_heuristic", "strength": 0.75}]
        g2 = [{"gene_name": "gene_b", "gene_type": "risk_heuristic", "strength": 0.80}]
        assert compute_dna_fingerprint(g1) != compute_dna_fingerprint(g2)

    def test_order_invariant(self):
        g1 = [
            {"gene_name": "a", "gene_type": "risk_heuristic", "strength": 0.70},
            {"gene_name": "b", "gene_type": "negotiation_pattern", "strength": 0.60},
        ]
        g2 = [g1[1], g1[0]]  # reversed order
        assert compute_dna_fingerprint(g1) == compute_dna_fingerprint(g2)


class TestPassportService:
    def test_issue_returns_string(self):
        svc = make_service
        passport = make_passport
        token = svc.issue(passport)
        assert isinstance(token, str) and len(token) > 50

    def test_verify_valid_token(self):
        svc = make_service
        token = svc.issue(make_passport)
        decoded = svc.verify(token)
        assert decoded["sub"] == "agent-001"
        assert "ag" in decoded

    def test_verify_ag_claims(self):
        svc = make_service
        token = svc.issue(make_passport(tier="T1", trust_score=0.95))
        decoded = svc.verify(token)
        ag = decoded["ag"]
        assert ag["tier"] == "T1"
        assert ag["trust_score"] == 0.9500
        assert "dna_fingerprint" in ag
        assert "allowed_environments" in ag

    def test_verify_expired_raises(self):
        svc = make_service(token_ttl_hours=0)
        p = make_passport
        p.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        token = jwt.encode(
            {"sub": "agent-001", "exp": int(p.expires_at.timestamp), "jti": p.jti, "ag": {}},
            SECRET, algorithm="HS256"
        )
        with pytest.raises(Exception):  # ExpiredSignatureError
            svc.verify(token)

    def test_verify_tampered_raises(self):
        svc = make_service
        token = svc.issue(make_passport)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(Exception):
            svc.verify(tampered)

    def test_revoke_blocks_verification(self):
        svc = make_service
        p = make_passport
        token = svc.issue(p)
        svc.revoke(p.jti)
        with pytest.raises(ValueError, match="revoked"):
            svc.verify(token)

    def test_revocation_list_export(self):
        svc = make_service
        p1 = make_passport
        p2 = make_passport(agent_id="agent-002")
        svc.issue(p1)
        svc.issue(p2)
        svc.revoke(p1.jti)
        rl = svc.get_revocation_list
        assert p1.jti in rl
        assert p2.jti not in rl

    def test_rotate_old_token_revoked(self):
        svc = make_service
        old_p = make_passport(tier="T3")
        old_token = svc.issue(old_p)
        new_p = make_passport(tier="T2")  # promotion
        svc.rotate(old_token, new_p)
        with pytest.raises((ValueError, Exception)):
            svc.verify(old_token)

    def test_rotate_new_token_valid(self):
        svc = make_service
        old_token = svc.issue(make_passport(tier="T3"))
        new_p = make_passport(tier="T2", agent_id="agent-001")
        new_token = svc.rotate(old_token, new_p)
        decoded = svc.verify(new_token)
        assert decoded["ag"]["tier"] == "T2"
