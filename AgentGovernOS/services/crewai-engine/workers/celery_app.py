"""
Celery application — task scheduling for Meta Crew and QICACHE eviction.

Workers are started separately from the CrewAI engine:
    celery -A workers.celery_app worker --loglevel=info
    celery -A workers.celery_app beat --loglevel=info
"""

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "agentgovern",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "workers.tasks.meta_crew_tasks",
        "workers.tasks.cache_tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # Ack only after completion (reliability)
    worker_prefetch_multiplier=1,  # One task at a time per worker (LLM tasks are heavy)
)

app.conf.beat_schedule = {
    # Historian: brief daily check at 2 AM UTC
    "daily-fleet-check": {
        "task": "workers.tasks.meta_crew_tasks.daily_fleet_check",
        "schedule": crontab(hour=2, minute=0),
    },
    # Full governance sweep every Sunday at 3 AM UTC
    "weekly-full-sweep": {
        "task": "workers.tasks.meta_crew_tasks.weekly_full_sweep",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),
    },
    # Red Teamer: adversarial probe every 6 hours
    "red-team-sweep": {
        "task": "workers.tasks.meta_crew_tasks.red_team_probe",
        "schedule": timedelta(hours=6),
    },
    # QICACHE eviction: hourly cleanup
    "cache-eviction": {
        "task": "workers.tasks.cache_tasks.evict_expired_cache",
        "schedule": crontab(minute=0),
    },
}
