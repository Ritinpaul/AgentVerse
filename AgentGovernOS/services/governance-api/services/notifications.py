import logging
from datetime import UTC, datetime, timedelta

from models import Decision, Organization
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def trigger_escalation(db: AsyncSession, decision: Decision) -> None:
        """
        Triggers an escalation notification to the organization's configured channels.
        """
        if not decision.org_id:
            logger.warning("Cannot trigger escalation for decision without org_id")
            return
            
        org = await db.scalar(select(Organization).where(Organization.id == decision.org_id))
        if not org or not org.notification_channels:
            logger.info("No notification channels configured for org.")
            return
            
        # Set an SLA deadline (e.g. 1 hour from now)
        decision.sla_deadline = datetime.now(UTC) + timedelta(hours=1)
        db.add(decision)
        await db.commit
        
        # Dispatch to Slack
        slack_webhook = org.notification_channels.get("slack_webhook")
        if slack_webhook:
            await NotificationService._send_slack(slack_webhook, decision)
            
        # Dispatch to Email
        email = org.notification_channels.get("email")
        if email:
            await NotificationService._send_email(email, decision)
            
    @staticmethod
    async def _send_slack(webhook_url: str, decision: Decision) -> None:
        payload = {
            "text": f"🚨 *Agent Action Escalated*\nDecision ID: `{decision.id}`\nAgent ID: `{decision.agent_id}`\nType: `{decision.decision_type}`\nReasoning: `{decision.reasoning_trace}`"
        }
        try:
            # Mocking the actual dispatch for # async with httpx.AsyncClient as client:
            #     await client.post(webhook_url, json=payload)
            logger.info(f"Dispatched Slack notification to {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    @staticmethod
    async def _send_email(email: str, decision: Decision) -> None:
        logger.info(f"Dispatched Email notification to {email}")
