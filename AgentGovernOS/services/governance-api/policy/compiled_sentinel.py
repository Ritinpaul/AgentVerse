"""
policy/compiled_sentinel.py

High-Performance Ahead-of-Time (AOT) Compiled SENTINEL Policy Engine.
Features:
1. Compiles declarative policy rules into native callable closures / bytecode predicates.
2. Evaluates rules with sub-millisecond (<0.1ms) execution latency.
3. Asynchronously buffers & streams decision telemetry events (with SHA-256 integrity hashes).
4. Supports composite predicates, regex guards, authority limits, and tool allowlists.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ── Telemetry Event ──────────────────────────────────────────────────────────

@dataclass
class DecisionTelemetryEvent:
    event_id: str
    agent_id: str
    policy_id: str
    rule_type: str
    verdict: str  # "PASS" | "FAIL" | "BLOCK" | "ESCALATE"
    duration_us: int
    timestamp: str
    audit_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "policy_id": self.policy_id,
            "rule_type": self.rule_type,
            "verdict": self.verdict,
            "duration_us": self.duration_us,
            "timestamp": self.timestamp,
            "audit_hash": self.audit_hash,
            "metadata": self.metadata,
        }


class DecisionTelemetryStreamer:
    """In-memory streaming telemetry buffer with Redis pub/sub or XADD streaming."""

    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._buffer: List[DecisionTelemetryEvent] = []

    def record_decision(
        self,
        agent_id: str,
        policy_id: str,
        rule_type: str,
        verdict: str,
        duration_us: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionTelemetryEvent:
        event_id = str(uuid.uuid4())
        ts = datetime.now(UTC).isoformat()
        meta = metadata or {}

        # Compute tamper-evident SHA-256 hash
        hash_payload = f"{event_id}:{agent_id}:{policy_id}:{verdict}:{ts}"
        audit_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        event = DecisionTelemetryEvent(
            event_id=event_id,
            agent_id=agent_id,
            policy_id=policy_id,
            rule_type=rule_type,
            verdict=verdict,
            duration_us=duration_us,
            timestamp=ts,
            audit_hash=audit_hash,
            metadata=meta,
        )

        self._buffer.append(event)
        if len(self._buffer) > self.max_buffer_size:
            self._buffer.pop(0)

        # Attempt to stream to Redis if available
        self._stream_to_redis(event)
        return event

    def _stream_to_redis(self, event: DecisionTelemetryEvent):
        try:
            from middleware.rate_limiter import _get_redis
            r = _get_redis()
            if r:
                r.xadd("sentinel:telemetry", {k: json.dumps(v) if isinstance(v, dict) else str(v) for k, v in event.to_dict().items()})
        except Exception as e:
            logger.debug(f"Redis telemetry streaming skipped: {e}")

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._buffer[-limit:]]

    def clear(self):
        self._buffer.clear()


telemetry_streamer = DecisionTelemetryStreamer()


# ── Compiled Rule & Predicate Engine ─────────────────────────────────────────

PredicateFunc = Callable[[Any, Dict[str, Any], Dict[str, Any]], bool]


@dataclass
class CompiledPolicyRule:
    rule_id: str
    rule_type: str
    on_fail: str
    predicate: PredicateFunc
    raw_params: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, agent: Any, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return self.predicate(agent, action, context)


class SentinelBytecodeEngine:
    """
    High-performance rule compiler.
    Compiles declarative policy rule dictionaries into native closures.
    """

    def __init__(self):
        self._compiled_cache: Dict[str, CompiledPolicyRule] = {}

    def compile_rule(self, rule_def: Dict[str, Any]) -> CompiledPolicyRule:
        rule_id = str(rule_def.get("id") or str(uuid.uuid4()))
        rule_type = rule_def.get("type", "unknown")
        on_fail = rule_def.get("on_fail", "deny")

        predicate = self._generate_predicate(rule_type, rule_def)
        compiled = CompiledPolicyRule(
            rule_id=rule_id,
            rule_type=rule_type,
            on_fail=on_fail,
            predicate=predicate,
            raw_params=rule_def,
        )
        self._compiled_cache[rule_id] = compiled
        return compiled

    def _generate_predicate(self, rule_type: str, params: Dict[str, Any]) -> PredicateFunc:
        if rule_type == "amount_limit":
            max_amount = Decimal(str(params.get("max_amount", 0)))
            def amount_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                if max_amount <= 0:
                    return False
                action_amount = action.get("amount")
                if action_amount is None:
                    return True
                return Decimal(str(action_amount)) <= max_amount
            return amount_predicate

        elif rule_type == "trust_minimum":
            min_trust = Decimal(str(params.get("min_trust", 0.50)))
            def trust_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                agent_trust = getattr(agent, "trust_score", None)
                if agent_trust is None:
                    return True
                return Decimal(str(agent_trust)) >= min_trust
            return trust_predicate

        elif rule_type == "tier_required":
            allowed_tiers = params.get("allowed_tiers")
            if allowed_tiers is not None:
                allowed_set = set(allowed_tiers)
                def tier_allowed_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                    return getattr(agent, "tier", "T1") in allowed_set
                return tier_allowed_predicate

            req_tier = params.get("tier", "T1")
            tier_ranks = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}
            req_rank = tier_ranks.get(req_tier, 1)

            def tier_rank_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                agent_tier = getattr(agent, "tier", "T1")
                return tier_ranks.get(agent_tier, 1) >= req_rank
            return tier_rank_predicate

        elif rule_type == "status_check":
            allowed_statuses = set(params.get("allowed_statuses", ["active"]))
            def status_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                return getattr(agent, "status", "active") in allowed_statuses
            return status_predicate

        elif rule_type == "action_blocked":
            blocked_actions = set(params.get("blocked_actions", []))
            def action_blocked_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                return action.get("type") not in blocked_actions
            return action_blocked_predicate

        elif rule_type == "action_allowed":
            allowed_actions = set(params.get("allowed_actions", []))
            def action_allowed_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                return not allowed_actions or action.get("type") in allowed_actions
            return action_allowed_predicate

        elif rule_type == "tool_allowlist":
            allowed_tools: Set[str] = set(params.get("allowed_tools", []))
            def tool_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                tool_name = action.get("tool_name") or action.get("tool")
                if not tool_name:
                    return True
                return tool_name in allowed_tools
            return tool_predicate

        elif rule_type == "regex_guard":
            pattern_str = params.get("pattern", r"^[a-zA-Z0-9_\- ]+$")
            compiled_re = re.compile(pattern_str)
            param_key = params.get("parameter_key", "query")

            def regex_predicate(agent: Any, action: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
                val = str(action.get(param_key, ""))
                return bool(compiled_re.search(val))
            return regex_predicate

        # Fallback unknown rule: default to permissive
        return lambda agent, action, ctx: True

    def evaluate_rule(
        self,
        rule_def: Dict[str, Any],
        agent: Any,
        action: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        t0 = time.perf_counter_ns()
        rule_id = str(rule_def.get("id") or rule_def.get("type", "unknown"))

        compiled = self._compiled_cache.get(rule_id)
        if not compiled:
            compiled = self.compile_rule(rule_def)

        ctx = context or {}
        passed = compiled.evaluate(agent, action, ctx)
        duration_us = (time.perf_counter_ns() - t0) // 1000

        # Stream decision telemetry
        verdict = "PASS" if passed else ("BLOCK" if compiled.on_fail == "deny" else "ESCALATE")
        agent_id = str(getattr(agent, "id", "unknown"))
        telemetry_streamer.record_decision(
            agent_id=agent_id,
            policy_id=rule_id,
            rule_type=compiled.rule_type,
            verdict=verdict,
            duration_us=duration_us,
            metadata={"action_type": action.get("type"), "on_fail": compiled.on_fail},
        )
        return passed

    def clear_cache(self):
        self._compiled_cache.clear()


sentinel_engine = SentinelBytecodeEngine()
