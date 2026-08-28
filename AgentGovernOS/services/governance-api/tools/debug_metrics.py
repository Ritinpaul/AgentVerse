"""Debug script to test the governance metrics logic directly."""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import UTC, datetime, timedelta

from config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory as db:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat
        hour_ago = (now - timedelta(hours=1)).isoformat

        try:
            # Verdict counts
            print("Testing verdict query...")
            verdict_rows = await db.execute(
                text("SELECT verdict, COUNT(*) AS cnt FROM audit_log GROUP BY verdict")
            )
            verdict_counts = {r.verdict: r.cnt for r in verdict_rows.mappings}
            print("Verdict counts:", verdict_counts)

            # Active agents
            print("Testing active agents...")
            fleet_row = await db.execute(
                text("SELECT COUNT(*) AS cnt FROM agents WHERE status = 'active'")
            )
            active_agents = (fleet_row.mappings.first or {}).get("cnt", 0)
            print("Active agents:", active_agents)

            # Escalations
            print("Testing escalation_cases...")
            esc_row = await db.execute(
                text("SELECT COUNT(*) AS cnt FROM escalation_cases WHERE status = 'pending'")
            )
            pending_escalations = (esc_row.mappings.first or {}).get("cnt", 0)
            print("Pending escalations:", pending_escalations)

            # Today eval count
            print("Testing today evals...")
            today_row = await db.execute(
                text("SELECT COUNT(*) AS cnt FROM audit_log WHERE created_at >= :ts"),
                {"ts": today_start},
            )
            evaluated_today = (today_row.mappings.first or {}).get("cnt", 0)
            print("Evaluated today:", evaluated_today)

        except Exception as e:
            import traceback
            print("EXCEPTION:", e)
            traceback.print_exc

    await engine.dispose


asyncio.run(main)
