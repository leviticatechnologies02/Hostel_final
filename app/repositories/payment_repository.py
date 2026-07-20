from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.booking import Booking
from app.models.payment import Payment
from app.models.student import Student


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_student_by_user(self, user_id: str) -> Student | None:
        result = await self.session.execute(select(Student).where(Student.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_by_student(self, student_id: str) -> list[Payment]:
        """Fetch payments directly linked to student_id (post check-in rent payments)."""
        result = await self.session.execute(
            select(Payment).where(Payment.student_id == student_id).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_user(self, user_id: str) -> list[Payment]:
        """
        Fetch ALL payments for a user — covering both:
        1. Payments linked via student_id (post check-in / rent).
        2. Payments linked only via booking_id (booking-advance before check-in),
           where the booking belongs to this visitor/user.

        This is the correct query for the student payments page because
        booking-advance payments are stored with student_id=NULL.
        """
        # Sub-query: booking IDs owned by this user
        booking_ids_subq = (
            select(Booking.id).where(Booking.visitor_id == user_id)
        ).scalar_subquery()

        # Get the student id for this user (may be None before check-in)
        student_row = await self.get_student_by_user(user_id)
        student_id = str(student_row.id) if student_row else None

        filters = [Payment.booking_id.in_(booking_ids_subq)]
        if student_id:
            filters.append(Payment.student_id == student_id)

        result = await self.session.execute(
            select(Payment)
            .options(joinedload(Payment.booking).joinedload(Booking.payments))
            .where(or_(*filters))
            .order_by(Payment.created_at.desc())
        )
        # Use unique() to deduplicate in case a payment matches both conditions
        return list(result.scalars().unique().all())

    async def list_by_hostel(self, hostel_id: str) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .options(joinedload(Payment.booking).joinedload(Booking.payments))
            .where(Payment.hostel_id == hostel_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().unique().all())
