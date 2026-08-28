"""
Gene Registry — persists and retrieves agent genes from PostgreSQL.

Wraps all DB interactions for GENESIS gene management:
  - store    : Save extracted genes
  - get      : Retrieve genes for an agent
  - update_strength : Mutate gene based on task outcome
  - certify  : Mark agent's DNA as ready for inheritance
  - audit    : Return integrity report
"""

import json
import logging
from datetime import UTC, datetime

from genesis.dna_sequencer import Gene

logger = logging.getLogger(__name__)


class GeneRegistry:
    """
    PostgreSQL-backed gene store.
    Uses sync SQLAlchemy (compatible with both Celery tasks and FastAPI via run_sync).
    """

    def __init__(self, db):
        """
        Args:
            db: SQLAlchemy session (sync or async — caller's responsibility).
        """
        self.db = db

    def store(self, genes: list[Gene]) -> int:
        """Persist a list of genes. Returns number stored."""
        from sqlalchemy import text

        stored = 0
        for gene in genes:
            try:
                self.db.execute(
                    text(
                        """
                        INSERT INTO agent_genes (
                            id, agent_id, gene_name, gene_type,
                            acquired_from, source_task_id,
                            version, strength, mutation_log,
                            created_at, updated_at
                        ) VALUES (
                            :id, :agent_id, :gene_name, :gene_type,
                            :acquired_from, :source_task_id,
                            :version, :strength, :mutation_log::jsonb,
                            :created_at, :updated_at
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            strength = EXCLUDED.strength,
                            mutation_log = EXCLUDED.mutation_log,
                            updated_at = NOW
                        """
                    ),
                    {
                        "id": gene.id,
                        "agent_id": gene.agent_id,
                        "gene_name": gene.gene_name[:100],
                        "gene_type": gene.gene_type,
                        "acquired_from": gene.acquired_from,
                        "source_task_id": gene.source_task_id or "",
                        "version": gene.version,
                        "strength": float(gene.strength),
                        "mutation_log": json.dumps(gene.mutation_log),
                        "created_at": gene.created_at,
                        "updated_at": datetime.now(UTC),
                    },
                )
                stored += 1
            except Exception as e:
                logger.warning(f"[GeneRegistry] Failed to store gene {gene.gene_name}: {e}")

        if stored:
            self.db.commit
        logger.info(f"[GeneRegistry] Stored {stored}/{len(genes)} genes")
        return stored

    def get_for_agent(self, agent_id: str, min_strength: float = 0.0) -> list[dict]:
        """Retrieve all genes for an agent above a minimum strength threshold."""
        from sqlalchemy import text

        try:
            rows = self.db.execute(
                text(
                    """
                    SELECT id, agent_id, gene_name, gene_type, acquired_from,
                           source_task_id, version, strength, mutation_log, created_at
                    FROM agent_genes
                    WHERE agent_id = :agent_id AND strength >= :min_strength
                    ORDER BY strength DESC
                    """
                ),
                {"agent_id": agent_id, "min_strength": min_strength},
            ).fetchall

            return [
                {
                    "id": r[0],
                    "agent_id": str(r[1]),
                    "gene_name": r[2],
                    "gene_type": r[3],
                    "acquired_from": r[4],
                    "source_task_id": r[5],
                    "version": r[6],
                    "strength": float(r[7]),
                    "mutation_log": r[8] if isinstance(r[8], list) else [],
                    "created_at": r[9].isoformat if r[9] else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"[GeneRegistry] Failed to fetch genes: {e}")
            return []

    def update_strength(self, gene_id: str, delta: float) -> bool:
        """Mutate gene strength by delta (positive = strengthen, negative = weaken)."""
        from sqlalchemy import text

        try:
            self.db.execute(
                text(
                    """
                    UPDATE agent_genes
                    SET strength = GREATEST(0.0, LEAST(1.0, strength + :delta)),
                        mutation_log = mutation_log || :log_entry::jsonb,
                        updated_at = NOW
                    WHERE id = :gene_id
                    """
                ),
                {
                    "gene_id": gene_id,
                    "delta": delta,
                    "log_entry": json.dumps(
                        [{"type": "mutation", "delta": delta, "timestamp": datetime.now(UTC).isoformat}]
                    ),
                },
            )
            self.db.commit
            return True
        except Exception as e:
            logger.error(f"[GeneRegistry] Strength update failed: {e}")
            return False

    def audit_integrity(self, agent_id: str) -> dict:
        """
        Produce a DNA integrity report for an agent.
        Used by the Gene Auditor (Meta Crew).
        """
        genes = self.get_for_agent(agent_id)
        if not genes:
            return {"agent_id": agent_id, "status": "no_dna", "gene_count": 0}

        dominant = [g for g in genes if g["strength"] >= 0.85]
        weak = [g for g in genes if g["strength"] < 0.30]
        type_distribution = {}
        for g in genes:
            type_distribution[g["gene_type"]] = type_distribution.get(g["gene_type"], 0) + 1

        return {
            "agent_id": agent_id,
            "status": "healthy" if not weak else "review_needed",
            "gene_count": len(genes),
            "dominant_count": len(dominant),
            "weak_count": len(weak),
            "avg_strength": round(sum(g["strength"] for g in genes) / len(genes), 4),
            "type_distribution": type_distribution,
            "dominant_genes": [g["gene_name"] for g in dominant],
            "retirement_candidates": [g["gene_name"] for g in weak],
        }
