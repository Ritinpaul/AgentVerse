import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        try:
            r = await conn.execute(text("SELECT COUNT(*) AS cnt FROM escalation_cases WHERE status = 'pending'"))
            print('escalation_cases pending:', list(r))
        except Exception as e:
            print('ERROR escalation_cases:', e)
    await engine.dispose

asyncio.run(main)
