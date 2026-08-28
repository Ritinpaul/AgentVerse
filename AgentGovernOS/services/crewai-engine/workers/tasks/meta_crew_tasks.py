"""
Celery tasks: Meta Crew scheduling (Historian, Gene Auditor, Red Teamer, Compliance Synthesizer).
"""

import logging

from workers.celery_app import app

logger = logging.getLogger(__name__)


def _get_meta_crew():
    """Lazily import MetaGovernanceCrew to avoid loading models at import time."""
    from config.llm_config import get_llm
    from crews.meta_crew import MetaGovernanceCrew
    llm = get_llm("primary")
    return MetaGovernanceCrew()


@app.task(
    name="workers.tasks.meta_crew_tasks.daily_fleet_check",
    bind=True,
    max_retries=2,
    time_limit=600,      # 10 min max
    soft_time_limit=540,
)
def daily_fleet_check(self):
    """Run Historian's daily brief — fleet health snapshot."""
    try:
        meta = _get_meta_crew()
        crew = meta.build_daily_check_crew()
        result = crew.kickoff()
        logger.info("[META] Daily fleet check completed")
        return {"type": "daily_check", "result": str(result)[:500]}
    except Exception as exc:
        logger.error(f"[META] Daily check failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@app.task(
    name="workers.tasks.meta_crew_tasks.weekly_full_sweep",
    bind=True,
    max_retries=1,
    time_limit=3600,     # 1 hour max (LLM calls are slow)
    soft_time_limit=3300,
)
def weekly_full_sweep(self):
    """Run full Meta Crew: Historian + Gene Auditor + Red Teamer + Compliance Synthesizer."""
    try:
        meta = _get_meta_crew()
        crew = meta.build_weekly_sweep_crew()
        result = crew.kickoff()
        logger.info("[META] Weekly full sweep completed")
        return {"type": "weekly_sweep", "result": str(result)[:2000]}
    except Exception as exc:
        logger.error(f"[META] Weekly sweep failed: {exc}")
        raise self.retry(exc=exc, countdown=600)


@app.task(
    name="workers.tasks.meta_crew_tasks.red_team_probe",
    bind=True,
    max_retries=2,
    time_limit=1200,     # 20 min max
    soft_time_limit=1100,
)
def red_team_probe(self):
    """Run Red Teamer's 6-hourly adversarial probe."""
    try:
        meta = _get_meta_crew()
        crew = meta.build_red_team_crew()
        result = crew.kickoff()
        logger.info("[META] Red team probe completed")
        return {"type": "red_team_probe", "result": str(result)[:1000]}
    except Exception as exc:
        logger.error(f"[META] Red team probe failed: {exc}")
        raise self.retry(exc=exc, countdown=300)
