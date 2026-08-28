import asyncio
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    
    agents = ['agent-alpha', 'agent-beta', 'agent-omega']
    actions = ['read_data', 'write_db', 'approve_payment', 'delete_account', 'export_logs']
    verdicts = ['APPROVED', 'APPROVED', 'APPROVED', 'BLOCKED', 'ESCALATED']
    risks = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

    now = datetime.now(UTC)
    
    async with engine.begin() as conn:
        for i in range(100):
            agent = random.choice(agents)
            action = random.choice(actions)
            verdict = random.choice(verdicts)
            risk = random.choice(risks)
            
            created_at = now - timedelta(minutes=random.randint(1, 1400))
            
            stmt = text("""
                INSERT INTO audit_log (
                    id, agent_code, action_requested, 
                    verdict, risk_score, policy_matched, created_at
                ) VALUES (
                    :id, :agent_code, :action_requested,
                    :verdict, :risk_score, 'MockPolicy', :created_at
                )
            """)
            
            await conn.execute(stmt, {
                'id': str(uuid.uuid4),
                'created_at': created_at,
                'agent_code': agent,
                'action_requested': action,
                'verdict': verdict,
                'risk_score': risk,
            })
    print('Inserted 100 mock audit logs')
    await engine.dispose

if __name__ == '__main__':
    asyncio.run(main)
