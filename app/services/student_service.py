"""
StudentService — creates Student record from an approved+checked-in booking.
Called after BookingService.check_in_student() has already committed.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import BookingStatus
from app.repositories.booking_repository import BookingRepository
from app.repositories.student_repository import StudentRepository


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.booking_repository = BookingRepository(session)
        self.student_repository = StudentRepository(session)

    async def check_in_from_booking(self, *, booking_id: str, actor_id: str):
        """Create a Student record from a CHECKED_IN booking."""
        booking = await self.booking_repository.get_by_id(booking_id)
        if booking is None:
            raise HTTPException(status_code=404, detail="Booking not found.")

        if booking.status != BookingStatus.CHECKED_IN:
            raise HTTPException(
                status_code=400,
                detail=f"Booking must be CHECKED_IN to create student record. Current: {booking.status.value}",
            )

        if booking.bed_id is None:
            raise HTTPException(status_code=400, detail="Booking has no allocated bed.")

        existing = await self.student_repository.get_student_by_booking(str(booking.id))
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Student record already exists for this booking.",
            )

        # Create student record
        student = await self.student_repository.create_from_booking(booking=booking)

        # Link BedStay to student
        await self.student_repository.activate_bed_stay(str(booking.id), str(student.id))

        # Promote user role to student
        await self.student_repository.promote_user_to_student(str(booking.visitor_id))

        # ✨ REVOKE ALL EXISTING TOKENS - Force re-login
        from app.repositories.user_repository import UserRepository
        from datetime import UTC, datetime
        
        repo = UserRepository(self.session)
        await repo.revoke_all_refresh_tokens(
            user_id=str(booking.visitor_id),
            revoked_at=datetime.now(UTC)
        )
        await self.session.commit()
        
        await self.session.refresh(student)
        return student