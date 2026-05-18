"""
Background booking lifecycle tasks.
"""
from datetime import UTC, datetime

from sqlalchemy import select

from app.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.booking import Booking, BookingStatus
from app.repositories.booking_repository import BookingRepository


@celery_app.task(bind=True, max_retries=3, ignore_result=True)
def expire_draft_booking_task(self, booking_id: str):
    """
    Expire a DRAFT booking after 30 minutes if still unpaid.
    """
    import asyncio
    
    async def _run():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Booking).where(Booking.id == booking_id))
            booking = result.scalar_one_or_none()
            if booking is None:
                return
            if booking.status != BookingStatus.DRAFT:
                return

            # Guard against race: only expire drafts older than 30 mins
            age_seconds = (datetime.now(UTC) - booking.created_at).total_seconds()
            if age_seconds < 30 * 60:
                return

            old_status = booking.status
            booking.status = BookingStatus.CANCELLED
            booking.cancellation_reason = "Draft booking expired after 30 minutes."

            repo = BookingRepository(session)
            await repo.add_status_history(
                booking_id=str(booking.id),
                old_status=old_status,
                new_status=BookingStatus.CANCELLED,
                changed_by=None,
                note="Auto-expired draft booking after 30 minutes.",
            )
            await session.commit()

    try:
        asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)