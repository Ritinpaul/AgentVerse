"""
Tests: ANCESTOR Decision Ledger

Covers:
  - DecisionRecord computes hash on creation
  - verify returns True on untampered record
  - verify returns False after tampering
  - Hash is deterministic (same input → same hash)
  - Two records with different content → different hashes
  - Hash chain: record sets prev_hash correctly
  - chain linkage: second block's prev_hash = first block's hash
  - to_dict includes all required fields
  - verify_chain returns valid on empty/in-memory ledger
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "crewai-engine"))

import pytest
from ancestor.decision_ledger import DecisionRecord, DecisionLedger


def make_record(**kwargs) -> DecisionRecord:
    defaults = dict(
        agent_id="agent-001",
        task_id="task-001",
        decision_type="dispute_resolution",
        input_context={"dispute_id": "DISP-001", "amount": 15000},
        reasoning_trace="Customer provided valid invoice. Settlement option B approved.",
        output_action={"decision": "approve", "settlement": "option_b", "amount": 15000},
        confidence_score=0.91,
        amount_involved=15000.0,
    )
    defaults.update(kwargs)
    return DecisionRecord(**defaults)


class TestDecisionRecord:
    def test_hash_computed_on_init(self):
        r = make_record
        assert len(r.hash) == 64

    def test_verify_passes_on_clean_record(self):
        r = make_record
        assert r.verify is True

    def test_verify_fails_after_tamper(self):
        r = make_record
        original_hash = r.hash
        r.confidence_score = 0.01  # tamper
        # hash is stale — won't match recomputed
        assert r.verify is False

    def test_hash_is_deterministic(self):
        """Same created_at and inputs → same hash."""
        from datetime import datetime
        ts = datetime(2024, 1, 1, 0, 0, 0)
        r1 = make_record
        r1.timestamp = ts
        r1.id = "fixed-id"
        r1.hash = r1._compute_hash

        r2 = make_record
        r2.timestamp = ts
        r2.id = "fixed-id"
        r2.hash = r2._compute_hash

        assert r1.hash == r2.hash

    def test_different_content_different_hash(self):
        r1 = make_record(amount_involved=10000.0)
        r2 = make_record(amount_involved=99999.0)
        assert r1.hash != r2.hash

    def test_to_dict_has_required_fields(self):
        r = make_record
        d = r.to_dict
        for field in ["id", "agent_id", "decision_type", "hash", "prev_hash",
                      "confidence_score", "reasoning_trace", "output_action", "timestamp"]:
            assert field in d, f"Missing field: {field}"

    def test_prev_hash_default_empty(self):
        r = make_record
        assert r.prev_hash == ""


class TestDecisionLedger:
    def test_record_sets_last_hash(self):
        ledger = DecisionLedger(db=None)
        r = make_record
        h = ledger.record(r)
        assert ledger._last_hash == h

    def test_second_record_prev_hash_equals_first_hash(self):
        ledger = DecisionLedger(db=None)
        r1 = make_record
        h1 = ledger.record(r1)

        r2 = make_record(task_id="task-002", confidence_score=0.75)
        ledger.record(r2)
        assert r2.prev_hash == h1

    def test_chain_of_three(self):
        ledger = DecisionLedger(db=None)
        h1 = ledger.record(make_record(task_id="t1"))
        h2 = ledger.record(make_record(task_id="t2"))
        r3 = make_record(task_id="t3")
        ledger.record(r3)
        assert r3.prev_hash == h2

    def test_verify_chain_no_db_returns_ok(self):
        ledger = DecisionLedger(db=None)
        result = ledger.verify_chain
        assert result["valid"] is True

    def test_record_returns_64_char_hash(self):
        ledger = DecisionLedger(db=None)
        h = ledger.record(make_record)
        assert len(h) == 64

    def test_record_preserves_confidence_score(self):
        r = make_record(confidence_score=0.77)
        ledger = DecisionLedger(db=None)
        ledger.record(r)
        assert r.confidence_score == 0.77

    def test_multiple_records_all_valid(self):
        """All records should have their hashes verified after being chained."""
        ledger = DecisionLedger(db=None)
        records = [make_record(task_id=f"task-{i}") for i in range(5)]
        for r in records:
            ledger.record(r)
        for r in records:
            assert r.verify is True
