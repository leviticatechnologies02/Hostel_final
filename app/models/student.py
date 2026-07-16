from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import BedStay, Booking
    from app.models.hostel import Hostel
    from app.models.operations import AttendanceRecord, Complaint
    from app.models.payment import Payment
    from app.models.room import Bed, Room
    from app.models.user import User


class StudentStatus(str, enum.Enum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ON_LEAVE = "on_leave"


class Student(BaseModel):
    __tablename__ = "students"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    bed_id: Mapped[str] = mapped_column(ForeignKey("beds.id", ondelete="CASCADE"), index=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), unique=True)
    student_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    check_in_date: Mapped[date] = mapped_column(Date)
    check_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[StudentStatus] = mapped_column(
        Enum(StudentStatus), default=StudentStatus.ACTIVE
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User", back_populates="student_profile"
    )
    hostel: Mapped[Hostel] = relationship("Hostel")
    room: Mapped[Room] = relationship("Room")
    bed: Mapped[Bed] = relationship("Bed")
    booking: Mapped[Booking] = relationship("Booking", foreign_keys=[booking_id])
    complaints: Mapped[list[Complaint]] = relationship(
        "Complaint", back_populates="student", cascade="all, delete-orphan"
    )
    attendance_records: Mapped[list[AttendanceRecord]] = relationship(
        "AttendanceRecord", back_populates="student", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="student")
    bed_stays: Mapped[list[BedStay]] = relationship("BedStay", back_populates="student")
