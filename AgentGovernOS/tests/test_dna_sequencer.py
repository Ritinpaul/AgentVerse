"""
Tests: GENESIS DNA Sequencer

Covers:
  - Gene extraction from rich task output text
  - No genes on empty/irrelevant output
  - All 5 gene types detected correctly
  - Initial strength heuristics (escalation > resolution > risk...)
  - Strength bounds (0.0 - 1.0)
  - Gene.strengthen / weaken lifecycle
  - Gene.is_dominant property
  - Gene.is_candidate_for_retirement property
  - Gene name construction
  - Inheritance: dominant genes copied, weak genes skipped
  - Inheritance: strength decay on child (0.9x)
  - Inheritance: mutation_log updated
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "crewai-engine"))

from decimal import Decimal
from genesis.dna_sequencer import Gene, DNASequencer


# ──────────────────────────────────────────────
# Gene dataclass tests
# ──────────────────────────────────────────────

class TestGeneLifecycle:
    def test_initial_strength_default(self):
        g = Gene(agent_id="a1", gene_name="test:gene", gene_type="risk_heuristic")
        assert g.strength == Decimal("0.50")

    def test_strengthen_increases_strength(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="risk_heuristic")
        g.strengthen(0.10)
        assert g.strength == Decimal("0.60")

    def test_strengthen_capped_at_1(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="risk_heuristic",
                 strength=Decimal("0.98"))
        g.strengthen(0.05)
        assert g.strength == Decimal("1.00")

    def test_weaken_decreases_strength(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="risk_heuristic")
        g.weaken(0.10)
        assert g.strength == Decimal("0.40")

    def test_weaken_floored_at_0(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="risk_heuristic",
                 strength=Decimal("0.02"))
        g.weaken(0.10)
        assert g.strength == Decimal("0.00")

    def test_strengthen_logs_mutation(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="risk_heuristic")
        g.strengthen(0.05)
        assert len(g.mutation_log) == 1
        assert g.mutation_log[0]["type"] == "strengthen"

    def test_weaken_logs_mutation(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="risk_heuristic")
        g.weaken(0.05)
        assert len(g.mutation_log) == 1
        assert g.mutation_log[0]["type"] == "weaken"

    def test_is_dominant_above_threshold(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="escalation_trigger",
                 strength=Decimal("0.85"))
        assert g.is_dominant is True

    def test_is_not_dominant_below_threshold(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="escalation_trigger",
                 strength=Decimal("0.84"))
        assert g.is_dominant is False

    def test_retirement_candidate_below_0_3(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="evidence_method",
                 strength=Decimal("0.29"))
        assert g.is_candidate_for_retirement is True

    def test_not_retirement_candidate_at_0_3(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="evidence_method",
                 strength=Decimal("0.30"))
        assert g.is_candidate_for_retirement is False

    def test_to_dict_contains_is_dominant(self):
        g = Gene(agent_id="a1", gene_name="test", gene_type="risk_heuristic",
                 strength=Decimal("0.90"))
        d = g.to_dict
        assert "is_dominant" in d
        assert d["is_dominant"] is True


# ──────────────────────────────────────────────
# DNASequencer extraction tests
# ──────────────────────────────────────────────

class TestDNASequencerExtraction:
    RICH_OUTPUT = """
        Evidence collected:
        - Invoice INV-4521 verified and authenticated
        - Purchase order PO-78234 confirmed
        - Delivery receipt shows partial delivery on 2024-01-15
        
        Risk assessment:
        - Risk score: 0.42
        - Medium risk detected
        - No fraud indicators found
        
        Settlement analysis:
        - Proposing settlement option B (balanced approach)
        - Offering 10% reduction on disputed amount
        
        Final decision: resolution: approve
        Approved amount: ₹18,500
        Confidence score: 0.87
    """

    ESCALATION_OUTPUT = """
        Amount exceeds authority limit for T3 agent.
        Escalation required — routing to human reviewer.
        Confidence below 0.70 — escalation triggered.
    """

    def test_extracts_evidence_gene(self):
        seq = DNASequencer
        genes = seq.extract(self.RICH_OUTPUT, "agent-001", "task-001")
        types = {g.gene_type for g in genes}
        assert "evidence_method" in types

    def test_extracts_risk_gene(self):
        seq = DNASequencer
        genes = seq.extract(self.RICH_OUTPUT, "agent-001")
        types = {g.gene_type for g in genes}
        assert "risk_heuristic" in types

    def test_extracts_negotiation_gene(self):
        seq = DNASequencer
        genes = seq.extract(self.RICH_OUTPUT, "agent-001")
        types = {g.gene_type for g in genes}
        assert "negotiation_pattern" in types

    def test_extracts_resolution_gene(self):
        seq = DNASequencer
        genes = seq.extract(self.RICH_OUTPUT, "agent-001")
        types = {g.gene_type for g in genes}
        assert "resolution_template" in types

    def test_extracts_escalation_gene(self):
        seq = DNASequencer
        genes = seq.extract(self.ESCALATION_OUTPUT, "agent-001")
        types = {g.gene_type for g in genes}
        assert "escalation_trigger" in types

    def test_no_genes_on_empty_output(self):
        seq = DNASequencer
        genes = seq.extract("", "agent-001")
        assert genes == []

    def test_no_genes_on_irrelevant_output(self):
        seq = DNASequencer
        genes = seq.extract("Hello world. Today is a nice day.", "agent-001")
        assert genes == []

    def test_gene_has_correct_agent_id(self):
        seq = DNASequencer
        genes = seq.extract(self.ESCALATION_OUTPUT, "agent-abc-123")
        assert all(g.agent_id == "agent-abc-123" for g in genes)

    def test_gene_has_source_task_id(self):
        seq = DNASequencer
        genes = seq.extract(self.RICH_OUTPUT, "a1", task_id="task-xyz")
        assert all(g.source_task_id == "task-xyz" for g in genes)

    def test_escalation_gene_has_higher_initial_strength(self):
        """Escalation genes should start stronger than evidence genes."""
        seq = DNASequencer
        esc_genes = seq.extract(self.ESCALATION_OUTPUT, "a1")
        esc_gene = next(g for g in esc_genes if g.gene_type == "escalation_trigger")
        ev_genes = seq.extract(self.RICH_OUTPUT, "a1")
        ev_gene = next(g for g in ev_genes if g.gene_type == "evidence_method")
        assert esc_gene.strength >= ev_gene.strength


# ──────────────────────────────────────────────
# DNASequencer inheritance tests
# ──────────────────────────────────────────────

class TestDNAInheritance:
    def _make_gene(self, strength: float, gene_type: str = "risk_heuristic") -> Gene:
        return Gene(
            agent_id="parent-1",
            gene_name=f"parent:{gene_type}:test",
            gene_type=gene_type,
            strength=Decimal(str(strength)),
        )

    def test_all_strong_genes_inherited_by_default(self):
        seq = DNASequencer
        parent_genes = [self._make_gene(0.60), self._make_gene(0.75)]
        children = seq.inherit(parent_genes, "child-1")
        assert len(children) == 2

    def test_weak_genes_not_inherited(self):
        seq = DNASequencer
        parent_genes = [self._make_gene(0.25), self._make_gene(0.70)]
        children = seq.inherit(parent_genes, "child-1")
        assert len(children) == 1
        assert float(children[0].strength) > 0.30

    def test_dominant_only_flag(self):
        seq = DNASequencer
        parent_genes = [
            self._make_gene(0.60),   # not dominant
            self._make_gene(0.90),   # dominant
        ]
        children = seq.inherit(parent_genes, "child-1", inherit_dominant_only=True)
        assert len(children) == 1
        assert float(children[0].strength) >= 0.85 * 0.90  # 0.9x decay applied

    def test_child_has_correct_agent_id(self):
        seq = DNASequencer
        parent_genes = [self._make_gene(0.75)]
        children = seq.inherit(parent_genes, "child-999")
        assert children[0].agent_id == "child-999"

    def test_strength_decayed_by_10_pct_on_inheritance(self):
        seq = DNASequencer
        parent_genes = [self._make_gene(0.80)]
        children = seq.inherit(parent_genes, "child-1")
        expected = Decimal("0.80") * Decimal("0.90")
        assert children[0].strength == expected

    def test_version_incremented(self):
        seq = DNASequencer
        parent_gene = self._make_gene(0.75)
        parent_gene.version = 2
        children = seq.inherit([parent_gene], "child-1")
        assert children[0].version == 3

    def test_mutation_log_has_inherited_from_entry(self):
        seq = DNASequencer
        parent_gene = self._make_gene(0.75)
        children = seq.inherit([parent_gene], "child-1")
        assert len(children[0].mutation_log) == 1
        assert children[0].mutation_log[0]["type"] == "inherited_from"

    def test_acquired_from_set_to_inherited(self):
        seq = DNASequencer
        parent_gene = self._make_gene(0.75)
        children = seq.inherit([parent_gene], "child-1")
        assert children[0].acquired_from == "inherited"
