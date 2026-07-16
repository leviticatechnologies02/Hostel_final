from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.hostel import Hostel
    from app.models.student import Student


class Complaint(BaseModel):
    __tablename__ = "complaints"

    complaint_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped[Student] = relationship("Student", back_populates="complaints")
    hostel: Mapped[Hostel] = relationship("Hostel")
    comments: Mapped[list[ComplaintComment]] = relationship(
        "ComplaintComment", back_populates="complaint", cascade="all, delete-orphan"
    )


class ComplaintComment(BaseModel):
    __tablename__ = "complaint_comments"

    complaint_id: Mapped[str] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)

    complaint: Mapped[Complaint] = relationship("Complaint", back_populates="comments")


class AttendanceRecord(BaseModel):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_attendance_student_date"),
    )

    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    check_in_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    marked_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    method: Mapped[str] = mapped_column(String(50))
    remarks: Mapped[str | None] = mapped_column(String(255), nullable=True)

    student: Mapped[Student] = relationship("Student", back_populates="attendance_records")
    hostel: Mapped[Hostel] = relationship("Hostel")


class MaintenanceRequest(BaseModel):
    __tablename__ = "maintenance_requests"

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True)
    reported_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    assigned_vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_contact: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scheduled_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requires_admin_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    hostel: Mapped[Hostel] = relationship("Hostel")


class Notice(BaseModel):
    __tablename__ = "notices"

    hostel_id: Mapped[str | None] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    notice_type: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(50))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    publish_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class NoticeRead(BaseModel):
    __tablename__ = "notice_reads"
    __table_args__ = (
        UniqueConstraint("notice_id", "user_id", name="uq_notice_read_notice_user"),
    )

    notice_id: Mapped[str] = mapped_column(
        ForeignKey("notices.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class MessMenu(BaseModel):
    __tablename__ = "mess_menus"

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    week_start_date: Mapped[date] = mapped_column(Date, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))

    items: Mapped[list[MessMenuItem]] = relationship(
        "MessMenuItem", back_populates="menu", cascade="all, delete-orphan"
    )


class MessMenuItem(BaseModel):
    __tablename__ = "mess_menu_items"

    menu_id: Mapped[str] = mapped_column(
        ForeignKey("mess_menus.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[str] = mapped_column(String(20))
    meal_type: Mapped[str] = mapped_column(String(50))
    item_name: Mapped[str] = mapped_column(String(255))
    is_veg: Mapped[bool] = mapped_column(Boolean, default=True)
    special_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    menu: Mapped[MessMenu] = relationship("MessMenu", back_populates="items")



class Subscription(BaseModel):
    __tablename__ = "subscriptions"

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[str | None] = mapped_column(
        ForeignKey("plans.id"), nullable=True, index=True
    )
    tier: Mapped[str] = mapped_column(String(50))
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50))
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    hostel: Mapped[Hostel] = relationship("Hostel")
    plan: Mapped[Plan | None] = relationship("Plan", back_populates="subscriptions")

class Review(BaseModel):
    __tablename__ = "reviews"

    visitor_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    booking_id: Mapped[str | None] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True)
    overall_rating: Mapped[float]
    cleanliness_rating: Mapped[float]
    food_rating: Mapped[float]
    security_rating: Mapped[float]
    value_rating: Mapped[float]
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
