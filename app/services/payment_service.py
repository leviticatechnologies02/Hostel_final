from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.payment_repository import PaymentRepository


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PaymentRepository(session)

    async def list_student_payments(self, *, user_id: str):
        """
        Return all payments for this user — includes:
        - Booking-advance payments (student_id=NULL, linked via booking_id)
        - Post check-in rent/deposit payments (linked via student_id)
        """
        return await self.repository.list_by_user(user_id)

    async def list_admin_payments(self, *, hostel_id: str):
        return await self.repository.list_by_hostel(hostel_id)
