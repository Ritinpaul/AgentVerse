"""DNA Engine — Gene inheritance, mutation validation, fitness scoring, and diff.

This service layer is the authoritative logic for Decision DNA operations:
  - create_initial_dna: baseline profile for a new agent, tuned by tier
  - inherit_dna: child profile shaped by a parent (70% parent / 30% default)
  - validate_mutation: guard rails before applying a trait delta
  - fitness_score: holistic DNA health grade (A–F)
  - diff_dna: trait-by-trait comparison between two agents
  - compute_dna_hash: stable SHA-256 fingerprint of a DNA profile

Used by:
  - GENESIS router (mutation + lineage endpoints)
  - CrewAI Engine (gene inheritance when spawning child agents)
  - Audit Ledger (DNA snapshot at decision time)
"""

import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Default values and constants
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_DNA_TRAITS: dict[str, float] = {
    "compliance_threshold": 0.75,
    "caution_factor": 0.50,
    "learning_rate": 0.10,
    "delegation_bias": 0.30,
    "risk_appetite": 0.40,
    "escalation_sensitivity": 0.60,
    "authority_ambition": 0.20,
    "collaboration_index": 0.50,
}

INHERITANCE_WEIGHT: float = 0.70

MUTATION_BOUNDS: dict[str, tuple[float, float]] = {
    "compliance_threshold": (0.30, 1.00),
    "caution_factor": (0.10, 0.90),
    "learning_rate": (0.01, 0.50),
    "delegation_bias": (0.00, 1.00),
    "risk_appetite": (0.05, 0.95),
    "escalation_sensitivity": (0.20, 1.00),
    "authority_ambition": (0.00, 0.80),
    "collaboration_index": (0.00, 1.00),
}

IDEAL_RANGES: dict[str, tuple[float, float, str]] = {
    "compliance_threshold": (0.70, 1.00, "high compliance is desirable"),
    "caution_factor": (0.30, 0.70, "balanced caution prevents both recklessness and paralysis"),
    "learning_rate": (0.05, 0.30, "too fast = unstable, too slow = stagnant"),
    "delegation_bias": (0.20, 0.70, "balanced delegation promotes team effectiveness"),
    "risk_appetite": (0.20, 0.60, "moderate risk tolerance"),
    "escalation_sensitivity": (0.40, 0.80, "catches real issues without alarm fatigue"),
    "authority_ambition": (0.10, 0.50, "some ambition is healthy, too much is dangerous"),
    "collaboration_index": (0.40, 0.90, "high collaboration improves outcomes"),
}

TIER_MODIFIERS: dict[str, dict[str, float]] = {
    "T1": {"compliance_threshold": 0.90, "risk_appetite": 0.20, "authority_ambition": 0.60, "caution_factor": 0.65},
    "T2": {"compliance_threshold": 0.85, "risk_appetite": 0.30, "authority_ambition": 0.40, "caution_factor": 0.55},
    "T3": {"compliance_threshold": 0.80, "risk_appetite": 0.40, "authority_ambition": 0.25, "caution_factor": 0.50},
    "T4": {"compliance_threshold": 0.70, "risk_appetite": 0.50, "authority_ambition": 0.15, "caution_factor": 0.45},
}


class DNAEngine:
    """Core logic for agent Decision DNA operations."""

    def create_initial_dna(self, tier: str = "T4") -> dict[str, float]:
        """Return a default DNA profile for a new agent, tuned by tier."""
        dna = dict(DEFAULT_DNA_TRAITS)
        for trait, value in TIER_MODIFIERS.get(tier, {}).items():
            dna[trait] = value
        return dna

    def inherit_dna(
        self,
        parent_dna: dict,
        child_tier: str = "T4",
        inheritance_weight: float = INHERITANCE_WEIGHT,
    ) -> dict[str, float]:
        """Create a child DNA profile by inheriting from a parent."""
        default_dna = self.create_initial_dna(child_tier)
        child_dna: dict[str, float] = {}

        all_traits = set(list(parent_dna.keys()) + list(default_dna.keys()))
        for trait in all_traits:
            parent_val = float(parent_dna.get(trait, default_dna.get(trait, 0.5)))
            default_val = float(default_dna.get(trait, parent_val))
            inherited = round(
                parent_val * inheritance_weight + default_val * (1.0 - inheritance_weight), 4
            )
            if trait in MUTATION_BOUNDS:
                lo, hi = MUTATION_BOUNDS[trait]
                inherited = max(lo, min(hi, inherited))
            child_dna[trait] = inherited

        return child_dna

    def validate_mutation(
        self, trait: str, current_value: float, delta: float
    ) -> tuple[bool, str]:
        """Validate that a mutation delta is safe to apply."""
        if trait not in MUTATION_BOUNDS:
            return True, ""

        lo, hi = MUTATION_BOUNDS[trait]
        new_val = round(current_value + delta, 4)

        if new_val < lo:
            return False, (
                f"Mutation would push '{trait}' to {new_val:.4f} "
                f"(minimum allowed: {lo})"
            )
        if new_val > hi:
            return False, (
                f"Mutation would push '{trait}' to {new_val:.4f} "
                f"(maximum allowed: {hi})"
            )
        return True, ""

    def apply_mutation(
        self, dna: dict, trait: str, delta: float
    ) -> tuple[dict, float, float]:
        """Apply a validated delta to a DNA profile."""
        current = float(dna.get(trait, DEFAULT_DNA_TRAITS.get(trait, 0.5)))
        valid, err = self.validate_mutation(trait, current, delta)
        if not valid:
            raise ValueError(err)

        new_val = round(current + delta, 4)
        if trait in MUTATION_BOUNDS:
            lo, hi = MUTATION_BOUNDS[trait]
            new_val = max(lo, min(hi, new_val))

        updated = dict(dna)
        updated[trait] = new_val
        return updated, current, new_val

    def fitness_score(self, dna: dict) -> dict:
        """Calculate a holistic DNA fitness score for an agent."""
        if not dna:
            return {"score": 0.0, "grade": "F", "trait_health": {}, "total_traits": 0}

        trait_scores: dict[str, float] = {}
        unknown_traits: list[str] = []

        for trait, (lo, hi, _description) in IDEAL_RANGES.items():
            if trait not in dna:
                unknown_traits.append(trait)
                continue
            val = float(dna[trait])
            if lo <= val <= hi:
                trait_scores[trait] = 1.0
            else:
                distance = min(abs(val - lo), abs(val - hi))
                range_size = max(hi - lo, 0.01)
                trait_scores[trait] = max(0.0, round(1.0 - (distance / range_size) * 0.5, 4))

        if not trait_scores:
            return {"score": 0.0, "grade": "F", "trait_health": {}, "total_traits": len(dna)}

        score = round(sum(trait_scores.values()) / len(trait_scores), 4)

        if score >= 0.90:
            grade = "A"
        elif score >= 0.75:
            grade = "B"
        elif score >= 0.60:
            grade = "C"
        elif score >= 0.40:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": score,
            "grade": grade,
            "trait_health": trait_scores,
            "missing_traits": unknown_traits,
            "total_traits": len(dna),
        }

    def diff_dna(
        self,
        dna_a: dict,
        dna_b: dict,
        label_a: str = "agent_a",
        label_b: str = "agent_b",
    ) -> dict:
        """Compare two DNA profiles trait by trait."""
        keys_a = set(dna_a.keys())
        keys_b = set(dna_b.keys())

        common: list[dict] = []
        total_divergence = 0.0

        for trait in sorted(keys_a & keys_b):
            val_a = round(float(dna_a[trait]), 4)
            val_b = round(float(dna_b[trait]), 4)
            delta = round(val_b - val_a, 4)
            divergence = abs(delta)
            total_divergence += divergence

            if delta > 0.001:
                direction = "increased"
            elif delta < -0.001:
                direction = "decreased"
            else:
                direction = "unchanged"

            common.append({
                "trait": trait,
                label_a: val_a,
                label_b: val_b,
                "delta": delta,
                "divergence": round(divergence, 4),
                "direction": direction,
            })

        only_in_a = {k: round(float(dna_a[k]), 4) for k in sorted(keys_a - keys_b)}
        only_in_b = {k: round(float(dna_b[k]), 4) for k in sorted(keys_b - keys_a)}

        total_traits = len(keys_a | keys_b) or 1
        unique_penalty = (len(only_in_a) + len(only_in_b)) / total_traits
        avg_divergence = (total_divergence / len(common)) if common else 0.0
        divergence_score = round(min(avg_divergence + unique_penalty * 0.5, 1.0), 4)

        most_divergent = (
            max(common, key=lambda x: x["divergence"])["trait"] if common else None
        )

        return {
            "common_traits": common,
            f"only_in_{label_a}": only_in_a,
            f"only_in_{label_b}": only_in_b,
            "divergence_score": divergence_score,
            "summary": {
                "common_count": len(common),
                f"unique_to_{label_a}": len(only_in_a),
                f"unique_to_{label_b}": len(only_in_b),
                "most_divergent_trait": most_divergent,
            },
        }

    def compute_dna_hash(self, dna: dict) -> str:
        """Compute a stable 16-char SHA-256 fingerprint of a DNA profile."""
        canonical = json.dumps(dna, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# Module-level singleton for convenience import
_engine = DNAEngine()

create_initial_dna = _engine.create_initial_dna
inherit_dna = _engine.inherit_dna
validate_mutation = _engine.validate_mutation
apply_mutation = _engine.apply_mutation
fitness_score = _engine.fitness_score
diff_dna = _engine.diff_dna
compute_dna_hash = _engine.compute_dna_hash
