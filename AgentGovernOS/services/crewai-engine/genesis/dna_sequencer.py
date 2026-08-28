"""
GENESIS DNA Sequencer — extracts capability 'genes' from resolved tasks.

What is a gene?
  A gene is a named capability pattern extracted from an agent's task output.
  It records WHAT the agent did, HOW well it did it, and WHAT context triggered it.
  Genes accumulate over an agent's lifetime, forming its Decision DNA profile.

Gene lifecycle:
  1. Agent completes a task
  2. DNASequencer.extract parses the task output → gene dict
  3. GeneRegistry.store saves the gene to PostgreSQL
  4. On agent spawn → GeneRegistry.inherit copies selected genes to child agent
  5. On agent retire → GeneRegistry.certify marks stable genes for inheritance

Gene types:
  - negotiation_pattern : successful settlement strategies
  - risk_heuristic      : effective risk assessment rules
  - evidence_method     : document collection approaches
  - escalation_trigger  : conditions that correctly predicted escalation need
  - resolution_template : repeatable decision frameworks

Strength (0.0 - 1.0):
  - Starts at 0.50 on creation
  - +0.05 when gene leads to successful outcome
  - -0.05 when gene leads to failed outcome
  - Genes below 0.30 are candidates for retirement
  - Genes above 0.85 are 'dominant' — always inherited
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class Gene:
    """A single capability gene extracted from a task."""
    agent_id: str
    gene_name: str
    gene_type: str
    acquired_from: str = "task_completion"
    source_task_id: str = ""
    version: int = 1
    strength: Decimal = Decimal("0.50")
    mutation_log: list = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: str = field(default_factory=lambda: str(uuid.uuid4))

    def strengthen(self, delta: float = 0.05) -> None:
        """Mark gene as more effective based on outcome."""
        self.strength = min(Decimal("1.00"), self.strength + Decimal(str(delta)))
        self.mutation_log.append({
            "type": "strengthen",
            "delta": delta,
            "timestamp": datetime.now(UTC).isoformat,
        })

    def weaken(self, delta: float = 0.05) -> None:
        """Mark gene as less effective based on outcome."""
        self.strength = max(Decimal("0.00"), self.strength - Decimal(str(delta)))
        self.mutation_log.append({
            "type": "weaken",
            "delta": -delta,
            "timestamp": datetime.now(UTC).isoformat,
        })

    @property
    def is_dominant(self) -> bool:
        return self.strength >= Decimal("0.85")

    @property
    def is_candidate_for_retirement(self) -> bool:
        return self.strength < Decimal("0.30")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "gene_name": self.gene_name,
            "gene_type": self.gene_type,
            "acquired_from": self.acquired_from,
            "source_task_id": self.source_task_id,
            "version": self.version,
            "strength": float(self.strength),
            "mutation_log": self.mutation_log,
            "is_dominant": self.is_dominant,
        }


class DNASequencer:
    """
    Extracts capability genes from CrewAI task outputs.

    This is the core of the GENESIS module — converting raw task
    result text into structured, inheritable genetic information.
    """

    # Pattern → gene_type mapping
    GENE_PATTERNS = {
        "negotiation_pattern": [
            r"settlement option [ABC]",
            r"offer(?:ed|ing)? .{1,40}% (reduction|discount|credit)",
            r"propose[ds]? .{1,50}(payment plan|installment)",
            r"mutual(ly)? agreeable",
            r"counter.?offer",
        ],
        "risk_heuristic": [
            r"risk score[:=\s]+[\d.]+",
            r"(high|medium|low|critical) risk",
            r"fraud indicator",
            r"credit (score|limit|history)",
            r"red flag",
        ],
        "evidence_method": [
            r"invoice [A-Z0-9\-]+",
            r"purchase order [A-Z0-9\-]+",
            r"evidence (package|timeline|collected)",
            r"document (verified|authenticated|missing|suspicious)",
            r"delivery receipt",
        ],
        "escalation_trigger": [
            r"escal(ate|ation) (required|needed|to human|triggered)",
            r"exceed(s|ed)? authority limit",
            r"confidence (below|under|<) 0\.[0-9]+",
            r"human (review|oversight|approval) required",
        ],
        "resolution_template": [
            r"resolution[:=\s]+(approve|reject|partial|hold)",
            r"decision[:=\s]+(approve|reject|settle|escalate)",
            r"final (decision|verdict|ruling)",
            r"approved? amount[:=\s]+[₹$]?[\d,]+",
        ],
    }

    def extract(self, task_output: str, agent_id: str, task_id: str = "", agent_role: str = "") -> list[Gene]:
        """
        Parse task output text and extract genes.

        Args:
            task_output: Raw string output from a CrewAI task
            agent_id: ID of the agent that produced the output
            task_id: Source task ID for lineage tracking
            agent_role: Role of the agent (used to weight gene types)

        Returns:
            List of extracted Gene objects (may be empty)
        """
        genes = []
        output_lower = task_output.lower

        for gene_type, patterns in self.GENE_PATTERNS.items:
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, output_lower, re.IGNORECASE)
                matches.extend(found)

            if matches:
                # Summarize the first match as the gene name
                gene_name = self._build_gene_name(gene_type, matches, agent_role)
                gene = Gene(
                    agent_id=agent_id,
                    gene_name=gene_name,
                    gene_type=gene_type,
                    acquired_from="task_completion",
                    source_task_id=task_id,
                    strength=self._initial_strength(gene_type, len(matches)),
                )
                genes.append(gene)
                logger.debug(f"[DNA] Extracted gene: {gene_name} (type={gene_type}, strength={gene.strength})")

        logger.info(f"[DNA] Extracted {len(genes)} genes from task {task_id} for agent {agent_id}")
        return genes

    def inherit(self, parent_genes: list[Gene], child_agent_id: str, inherit_dominant_only: bool = False) -> list[Gene]:
        """
        Create inherited copies of parent genes for a child agent.

        Args:
            parent_genes: Genes from the parent agent
            child_agent_id: ID of the new child agent
            inherit_dominant_only: If True, only inherit genes with strength >= 0.85

        Returns:
            List of new Gene objects for the child
        """
        inherited = []
        for gene in parent_genes:
            if inherit_dominant_only and not gene.is_dominant:
                continue
            if gene.is_candidate_for_retirement:
                continue

            child_gene = Gene(
                agent_id=child_agent_id,
                gene_name=gene.gene_name,
                gene_type=gene.gene_type,
                acquired_from="inherited",
                source_task_id=gene.source_task_id,
                version=gene.version + 1,
                strength=gene.strength * Decimal("0.90"),  # slight decay on inheritance
                mutation_log=[{
                    "type": "inherited_from",
                    "parent_agent_id": gene.agent_id,
                    "parent_gene_id": gene.id,
                    "parent_strength": float(gene.strength),
                    "timestamp": datetime.now(UTC).isoformat,
                }],
            )
            inherited.append(child_gene)

        logger.info(
            f"[DNA] Inherited {len(inherited)}/{len(parent_genes)} genes "
            f"(dominant_only={inherit_dominant_only}) → agent {child_agent_id}"
        )
        return inherited

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _build_gene_name(gene_type: str, matches: list, agent_role: str) -> str:
        """Human-readable gene name from type + first match + role."""
        role_prefix = agent_role.split("_")[0] if agent_role else "agent"
        sample = str(matches[0])[:40].strip.replace("\n", " ")
        return f"{role_prefix}:{gene_type}:{sample}" if sample else f"{role_prefix}:{gene_type}"

    @staticmethod
    def _initial_strength(gene_type: str, match_count: int) -> Decimal:
        """
        Stronger initial strength for high-value gene types
        and when multiple pattern matches are found.
        """
        base = {
            "escalation_trigger": 0.70,  # Escalation genes are critical
            "resolution_template": 0.65,  # Resolution patterns are high value
            "risk_heuristic": 0.60,
            "negotiation_pattern": 0.55,
            "evidence_method": 0.50,
        }.get(gene_type, 0.50)

        # Bonus for multiple matches (gene is more prominent in this task)
        bonus = min(0.10, match_count * 0.02)
        return Decimal(str(round(base + bonus, 2)))
