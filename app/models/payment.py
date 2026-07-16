from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.hostel import Hostel
    from app.models.student import Student


class Payment(BaseModel):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "booking_id IS NOT NULL OR student_id IS NOT NULL",
            name="ck_payment_has_context",
        ),
    )

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str | None] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True
    )
    booking_id: Mapped[str | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    payment_type: Mapped[str] = mapped_column(String(50))
    payment_method: Mapped[str] = mapped_column(String(50))
    gateway_order_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True
    )
    gateway_payment_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gateway_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    hostel: Mapped[Hostel] = relationship("Hostel")
    student: Mapped[Student | None] = relationship("Student", back_populates="payments")
    booking: Mapped[Booking | None] = relationship("Booking", back_populates="payments")


class PaymentWebhookEvent(BaseModel):
    __tablename__ = "payment_webhook_events"

    provider: Mapped[str] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[str] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
