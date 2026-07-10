# app/schemas/student.py

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.base import APIModel, TimestampedResponse


class StudentProfileResponse(TimestampedResponse):
    user_id: str
    hostel_id: str
    room_id: str
    bed_id: str
    booking_id: str
    student_number: str
    check_in_date: date
    check_out_date: date | None = None
    status: str
    full_name: str
    email: str
    phone: str
    profile_picture_url: str | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    hostel_name: str | None = None
    hostel_city: str | None = None
    hostel_type: str | None = None
    room_number: str | None = None
    bed_number: str | None = None
    booking_number: str | None = None
    booking_mode: str | None = None


class StudentResponse(TimestampedResponse):
    user_id: str
    hostel_id: str
    room_id: str
    bed_id: str
    booking_id: str
    student_number: str
    check_in_date: str
    check_out_date: str | None
    status: str
    full_name: str
    email: str
    phone: str
    profile_picture_url: str | None
    room_number: str | None = None
    bed_number: str | None = None
    gender: str | None = None  # ← ADD THIS
    date_of_birth: str | None = None  # ← ADD THIS (optional)


class CompleteStudentDetailResponse(APIModel):
    """Complete student details for admin view"""
    
    # Student identifiers
    id: str
    student_number: str
    user_id: str
    
    # Personal Information (from User table)
    full_name: str
    email: str
    phone: str
    gender: str | None = None
    date_of_birth: date | None = None
    profile_picture_url: str | None = None
    
    # Student Information
    status: str  # active, checked_out, on_leave
    check_in_date: date
    check_out_date: date | None = None
    
    # Room Information
    room_id: str
    room_number: str | None = None
    room_type: str | None = None
    floor: int | None = None
    monthly_rent: float | None = None
    daily_rent: float | None = None
    
    # Bed Information
    bed_id: str
    bed_number: str | None = None
    
    # Booking Information
    booking_id: str
    booking_number: str | None = None
    booking_mode: str | None = None  # daily / monthly
    
    # Hostel Information
    hostel_id: str
    hostel_name: str | None = None
    hostel_city: str | None = None
    hostel_type: str | None = None  # boys / girls / coed
    
    # Payment Information
    payment_status: str = "pending"  # paid, pending, overdue
    total_paid: float = 0.0
    last_payment_date: datetime | None = None
    next_payment_due: date | None = None
    advance_paid: float = 0.0
    
    # Additional Information
    occupation: str | None = None
    institution: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime


class StudentPaymentSummary(APIModel):
    """Payment summary for a student"""
    total_paid: float
    pending_amount: float
    last_payment_date: datetime | None
    last_payment_amount: float
    next_due_date: date | None
    payment_history: list[dict]
    

class StudentUpdateRequest(BaseModel):
    """Request model for updating student"""
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    phone: str | None = Field(default=None, min_length=8, max_length=30)
    student_number: str | None = Field(default=None, min_length=3, max_length=50)
    status: str | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
class StudentProfileUpdateRequest(BaseModel):
    """Request model for updating student profile"""
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=8, max_length=30)