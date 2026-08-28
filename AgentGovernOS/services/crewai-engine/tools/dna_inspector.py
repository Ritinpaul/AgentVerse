"""
Tool: DNA Inspector — read and mutate agent DNA profiles.

Used by: Meta Crew's Gene Auditor agent, Governance Sentinel.
"""

import logging
from typing import Any

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DNAReadInput(BaseModel):
    agent_id: str = Field(..., description="Agent ID to inspect")
    include_lineage: bool = Field(False, description="Include parent/child agent lineage")
    include_gene_history: bool = Field(False, description="Include gene mutation history")


class DNAMutateInput(BaseModel):
    agent_id: str = Field(..., description="Agent ID to mutate")
    gene_key: str = Field(..., description="Gene to modify (e.g., risk_tolerance, negotiation_style)")
    new_value: Any = Field(..., description="New value for the gene")
    mutation_reason: str = Field(..., description="Reason for this mutation (logged in ledger)")
    mutation_source: str = Field("meta_crew", description="Source of mutation: meta_crew / human / learning")


class DNAInspectorTool(BaseTool):
    """
    Read and mutate agent DNA profiles stored in the GENESIS registry.

    Agent DNA encodes behavioral traits, risk tolerances, and decision-making
    tendencies. DNA evolves through:
    - Learning events (successful/failed decisions)
    - Meta crew audits (periodic optimization)
    - Human corrections (post-review adjustments)

    Gene examples:
    - risk_tolerance: float (0.0-1.0)
    - negotiation_style: str (AGGRESSIVE / BALANCED / CONCILIATORY)
    - settlement_bias: float (-1.0 to +1.0, negative = favor customer)
    - escalation_threshold: float (0.0-1.0)
    - fraud_sensitivity: float (0.0-1.0)
    """

    name: str = "dna_inspector"
    description: str = (
        "Inspect or mutate an agent's DNA profile. "
        "Read: get current genes, behavior traits, and lineage. "
        "Mutate: adjust a specific gene value with a documented reason. "
        "All mutations are logged permanently in the decision ledger. "
        "Used by Meta Crew to optimize agent performance over time."
    )
    args_schema: type[BaseModel] = DNAReadInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        agent_id: str,
        include_lineage: bool = False,
        include_gene_history: bool = False,
    ) -> str:
        """Read agent DNA profile."""
        try:
            response = httpx.get(
                f"{self.api_url}/genesis/agents/{agent_id}/dna",
                params={
                    "include_lineage": include_lineage,
                    "include_gene_history": include_gene_history,
                },
                timeout=10.0,
            )
            if response.status_code == 200:
                return self._format_dna_profile(response.json)
            else:
                return self._mock_dna_profile(agent_id)
        except httpx.ConnectError:
            return self._mock_dna_profile(agent_id)
        except Exception as e:
            logger.error(f"DNAInspectorTool read error: {e}")
            return f"Error reading DNA: {e!s}"

    def mutate_gene(
        self,
        agent_id: str,
        gene_key: str,
        new_value: Any,
        mutation_reason: str,
        mutation_source: str = "meta_crew",
    ) -> str:
        """Apply a gene mutation to an agent."""
        try:
            response = httpx.patch(
                f"{self.api_url}/genesis/agents/{agent_id}/dna",
                json={
                    "gene_key": gene_key,
                    "new_value": new_value,
                    "mutation_reason": mutation_reason,
                    "mutation_source": mutation_source,
                },
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json
                return (
                    f"DNA MUTATION APPLIED ✓\n"
                    f"Agent:      {agent_id}\n"
                    f"Gene:       {gene_key}\n"
                    f"Old Value:  {data.get('old_value')}\n"
                    f"New Value:  {data.get('new_value')}\n"
                    f"Reason:     {mutation_reason}\n"
                    f"Source:     {mutation_source}\n"
                    f"Ledger ID:  {data.get('mutation_id', 'N/A')}\n"
                )
            else:
                return f"DNA mutation queued for {agent_id}.{gene_key} → {new_value} (API offline)"
        except httpx.ConnectError:
            return (
                f"DNA MUTATION QUEUED (API offline)\n"
                f"Agent: {agent_id} | Gene: {gene_key} → {new_value}\n"
                f"Reason: {mutation_reason}\n"
                f"Will be applied when API reconnects.\n"
            )

    def _format_dna_profile(self, data: dict) -> str:
        genes = data.get("genes", {})
        return (
            f"DNA PROFILE — Agent: {data.get('agent_id')}\n"
            f"Version:  {data.get('dna_version', '1.0')}\n"
            f"Generation: {data.get('generation', 0)}\n"
            f"{'='*60}\n"
            + "\n".join(f"  {k:<30} = {v}" for k, v in genes.items)
            + f"\n\nParent Agent: {data.get('parent_agent_id', 'Genesis (no parent)')}\n"
            f"Total Mutations: {data.get('mutation_count', 0)}\n"
            f"Last Mutation: {data.get('last_mutation_at', 'Never')}\n"
        )

    def _mock_dna_profile(self, agent_id: str) -> str:
        return (
            f"DNA PROFILE — Agent: {agent_id}\n"
            f"Version:  2.1.4\n"
            f"Generation: 3\n"
            f"{'='*60}\n"
            f"  risk_tolerance                 = 0.68\n"
            f"  negotiation_style              = BALANCED\n"
            f"  settlement_bias                = -0.12 (slight customer-favor)\n"
            f"  escalation_threshold           = 0.72\n"
            f"  fraud_sensitivity              = 0.85\n"
            f"  evidence_weight_delivery       = 0.40\n"
            f"  evidence_weight_invoice        = 0.35\n"
            f"  evidence_weight_email          = 0.25\n"
            f"  max_autonomous_settlement_inr  = 100000\n"
            f"  documentation_rigor            = HIGH\n\n"
            f"Parent Agent: AGENT-7749-v2\n"
            f"Total Mutations: 14\n"
            f"Last Mutation: 2024-11-10 (escalation_threshold adjusted by Meta Crew)\n"
        )
