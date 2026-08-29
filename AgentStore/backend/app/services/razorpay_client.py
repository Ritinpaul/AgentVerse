"""
Razorpay Client — Thin wrapper for subscription and payout operations.
"""
from __future__ import annotations
import os
import razorpay


def _get_client() -> razorpay.Client:
    key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "placeholder_secret")
    return razorpay.Client(auth=(key_id, key_secret))


def create_customer(org_id: str, email: str, name: str = "") -> dict:
    """Create a Razorpay customer for an organization."""
    client = _get_client()
    return client.customer.create({
        "name": name or org_id,
        "email": email,
        "notes": {"org_id": org_id},
    })


def create_subscription(customer_id: str, plan_id: str, total_count: int = 12) -> dict:
    """Create a Razorpay subscription for an org plan upgrade."""
    client = _get_client()
    return client.subscription.create({
        "plan_id": plan_id,
        "customer_id": customer_id,
        "total_count": total_count,
        "quantity": 1,
    })


def cancel_subscription(subscription_id: str) -> dict:
    """Cancel a Razorpay subscription."""
    client = _get_client()
    return client.subscription.cancel(subscription_id)


def create_payout(
    account_number: str,
    fund_account_id: str,
    amount_inr_paise: int,
    reference: str,
) -> dict:
    """Initiate a Razorpay Payout for builder revenue share."""
    client = _get_client()
    return client.payout.create({
        "account_number": account_number,
        "fund_account_id": fund_account_id,
        "amount": amount_inr_paise,
        "currency": "INR",
        "mode": "IMPS",
        "purpose": "payout",
        "narration": f"AgentStore Revenue: {reference}",
    })


def verify_webhook_signature(body: bytes, signature: str, webhook_secret: str) -> bool:
    """Verify Razorpay webhook payload authenticity."""
    import hmac
    import hashlib
    expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
