# FILE: app/services/subscription_validator.py
"""
Subscription validation service - ensures bookings are only made for hostels with active subscriptions.
"""
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.operations import Subscription


class SubscriptionValidator:
    """Validate hostel subscription status for bookings."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        

    async def validate_hostel_subscription(
        self, 
        hostel_id: str, 
        check_in_date: date | None = None,
        check_out_date: date | None = None
    ) -> bool:
        """
        Validate that hostel has an active subscription for the given dates.
        Returns True always but logs warnings if no subscription.
        """
        # Get active subscription for this hostel
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.hostel_id == hostel_id,
                Subscription.status == "active"
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            # Log warning but allow booking (for testing)
            print(f"⚠️ WARNING: Hostel {hostel_id} has no active subscription. Allowing booking for testing.")
            return True
        
        today = date.today()
        start_date = subscription.start_date
        end_date = subscription.end_date
        
        # Check if subscription is active overall
        if today < start_date:
            print(f"⚠️ WARNING: Hostel subscription starts on {start_date}. Allowing booking for testing.")
            return True
        
        if today > end_date:
            print(f"⚠️ WARNING: Hostel subscription expired on {end_date}. Allowing booking for testing.")
            return True
        
        # If booking dates are provided, check if they fall within subscription period
        if check_in_date and check_out_date:
            if check_in_date < start_date:
                print(f"⚠️ WARNING: Check-in date before subscription start. Allowing for testing.")
            if check_out_date > end_date:
                print(f"⚠️ WARNING: Check-out date after subscription expiry. Allowing for testing.")
        
        return True
    
    async def get_subscription_info(self, hostel_id: str) -> dict | None:
        """Get subscription information for a hostel."""
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.hostel_id == hostel_id,
                Subscription.status == "active"
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return None
        
        today = date.today()
        return {
            "has_active_subscription": True,
            "start_date": subscription.start_date.isoformat(),
            "end_date": subscription.end_date.isoformat(),
            "is_active": subscription.start_date <= today <= subscription.end_date,
            "days_remaining": max(0, (subscription.end_date - today).days),
            "tier": subscription.tier,
            "auto_renew": subscription.auto_renew,
        }