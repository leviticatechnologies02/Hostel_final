from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from app.dependencies import DBSession, CurrentUser, require_roles
from app.models.booking import Booking
from app.models.operations import MaintenanceRequest, Complaint
from app.schemas.admin import (
    AdminDashboardResponse,
    SupervisorResponse,
    SupervisorUpdateRequest,
    SupervisorCreateRequest,
    DirectStudentAddRequest,
    DirectStudentAddResponse,
)
from app.schemas.complaint import ComplaintUpdateRequest
from app.schemas.hostel import HostelDetailResponse, HostelUpdateRequest, HostelListItem
from app.schemas.room import (
    RoomResponse,
    RoomCreateRequest,
    RoomUpdateRequest,
    BedResponse,
    BedCreateRequest,
    BedUpdateRequest,
)

from app.schemas.booking import (
    BookingResponse,
    BookingApprovalRequest,
    BookingRejectionRequest,
    BookingCancellationRequest,
)
from pydantic import BaseModel, Field
import re
from datetime import UTC, datetime
from app.core.security import verify_password, hash_password
from app.repositories.user_repository import UserRepository
from app.schemas.student import CompleteStudentDetailResponse
from app.services.admin_service import AdminService
from app.schemas.payment import PaymentResponse
from app.schemas.complaint import ComplaintResponse
from app.schemas.attendance import AttendanceResponse, AttendanceMonthlySummaryItem
from app.schemas.maintenance import MaintenanceResponse, MaintenanceUpdateRequest
from app.schemas.notice import NoticeResponse, NoticeReadStatsItem, NoticeCreateRequest
from app.schemas.mess_menu import MessMenuResponse, MessMenuCreateRequest, MessMenuItemResponse
from app.schemas.student import StudentResponse, StudentUpdateRequest
from app.services.admin_service import AdminService
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.complaint_service import ComplaintService
from app.services.attendance_service import AttendanceService
from app.services.maintenance_service import MaintenanceService
from app.services.notice_service import NoticeService
from app.services.mess_menu_service import MessMenuService
from app.schemas.notice import NoticeCreateRequest, NoticeUpdateRequest, NoticeResponse
from app.schemas.mess_menu import MessMenuCreateRequest, MessMenuItemUpdateRequest
from starlette.responses import Response
from pydantic import ValidationError as PydanticValidationError


router = APIRouter()
AdminUser = Annotated[CurrentUser, Depends(require_roles("hostel_admin", "super_admin"))]


class AdminProfileResponse(BaseModel):
    """Admin profile response model"""
    id: str
    email: str
    phone: str
    full_name: str
    role: str
    profile_picture_url: str | None = None
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool
    assigned_hostels: list[dict] = []
    created_at: datetime
    updated_at: datetime

class AdminProfileUpdateRequest(BaseModel):
    """Request to update admin profile"""
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=8, max_length=30)

class AdminChangePasswordRequest(BaseModel):
    """Request to change admin password"""
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

def validate_phone_number(phone: str) -> str:
    """Validate and clean phone number"""
    import re
    
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required.")
    
    # Remove whitespace
    phone = phone.strip()
    
    # Remove common prefixes and special characters
    cleaned = re.sub(r'[^0-9+]', '', phone)
    
    # Handle +91 prefix
    if cleaned.startswith('+91'):
        cleaned = cleaned[3:]
    elif cleaned.startswith('91'):
        cleaned = cleaned[2:]
    elif cleaned.startswith('0'):
        cleaned = cleaned[1:]
    
    # Remove any remaining non-digits
    digits_only = re.sub(r'[^0-9]', '', cleaned)
    
    # Check length
    if len(digits_only) < 10:
        raise HTTPException(
            status_code=400,
            detail="Phone number must have at least 10 digits."
        )
    if len(digits_only) > 10:
        # If more than 10 digits, take last 10 if it's a valid Indian number
        if len(digits_only) > 10 and digits_only[-10] in ['6', '7', '8', '9']:
            digits_only = digits_only[-10:]
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number format. Please provide a 10-digit Indian number."
            )
    
    # Check first digit for Indian numbers
    if digits_only[0] not in ['6', '7', '8', '9']:
        raise HTTPException(
            status_code=400,
            detail="Indian phone number must start with 6, 7, 8, or 9."
        )
    
    return digits_only

def handle_validation_error(e: ValueError) -> None:
    """Convert Pydantic validation errors to HTTP 400"""
    raise HTTPException(status_code=400, detail=str(e))

def _check_hostel(current_user: AdminUser, hostel_id: str) -> None:
    if hostel_id not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied to this hostel.")


async def _resolve_room_hostel_id(db: DBSession, room_id: str) -> str:
    from app.models.room import Room
    result = await db.execute(select(Room.hostel_id).where(Room.id == room_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    return str(hostel_id)


async def _resolve_bed_hostel_id(db: DBSession, bed_id: str) -> str:
    from app.models.room import Bed
    result = await db.execute(select(Bed.hostel_id).where(Bed.id == bed_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Bed not found.")
    return str(hostel_id)


async def _resolve_booking_hostel_id(db: DBSession, booking_id: str) -> str:
    result = await db.execute(select(Booking.hostel_id).where(Booking.id == booking_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return str(hostel_id)


async def _resolve_maintenance_hostel_id(db: DBSession, request_id: str) -> str:
    result = await db.execute(select(MaintenanceRequest.hostel_id).where(MaintenanceRequest.id == request_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Maintenance request not found.")
    return str(hostel_id)


async def _resolve_complaint_hostel_id(db: DBSession, complaint_id: str) -> str:
    result = await db.execute(select(Complaint.hostel_id).where(Complaint.id == complaint_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return str(hostel_id)


@router.get("/my-hostels", response_model=list[HostelListItem])
async def my_hostels(current_user: AdminUser, db: DBSession):
    """List hostels assigned to the authenticated admin."""
    return await AdminService(db).list_hostels(list(current_user.hostel_ids))


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def dashboard(current_user: AdminUser, db: DBSession, hostel_id: str | None = None):
    """Admin dashboard metrics."""
    if hostel_id:
        _check_hostel(current_user, hostel_id)
        ids = [hostel_id]
    else:
        ids = list(current_user.hostel_ids)
    return await AdminService(db).get_dashboard(ids)


@router.get("/dashboard/unified")
async def unified_dashboard(_: AdminUser):
    """Unified multi-hostel dashboard (stub)."""
    return {"hostels": 0, "revenue": 0}


@router.get("/hostels/{hostel_id}", response_model=HostelDetailResponse)
async def get_hostel(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).get_hostel(hostel_id)


@router.patch("/hostels/{hostel_id}", response_model=HostelDetailResponse)
async def update_hostel(hostel_id: str, payload: HostelUpdateRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).update_hostel(hostel_id, payload)


@router.get("/hostels/{hostel_id}/bookings", response_model=list[BookingResponse])
async def list_bookings(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await BookingService(db).list_admin_bookings(hostel_id=hostel_id)


@router.get("/hostels/{hostel_id}/rooms", response_model=list[RoomResponse])
async def list_rooms(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).list_rooms(hostel_id)


@router.post("/hostels/{hostel_id}/rooms", response_model=RoomResponse, status_code=201)
async def create_room(
    hostel_id: str,
    payload: RoomCreateRequest,
    db: DBSession,
    current_user: AdminUser
):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).create_room(hostel_id, payload)


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(room_id: str, payload: RoomUpdateRequest, db: DBSession, current_user: AdminUser):
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    return await AdminService(db).update_room(room_id, payload)

@router.delete("/rooms/{room_id}", status_code=204)
async def delete_room(room_id: str, db: DBSession, current_user: AdminUser):
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    await AdminService(db).delete_room(room_id)


@router.get("/rooms/{room_id}/beds", response_model=List[BedResponse])
async def list_beds(room_id: str, db: DBSession, current_user: AdminUser):
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    return await AdminService(db).list_beds(room_id)


@router.post("/rooms/{room_id}/beds", response_model=BedResponse, status_code=201)
async def create_bed(room_id: str, payload: BedCreateRequest, db: DBSession, current_user: AdminUser):
    """Create a new bed in a room"""
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    
    try:
        return await AdminService(db).create_bed(room_id, payload)
    except Exception as e:
        # Check for unique constraint violation
        error_msg = str(e).lower()
        if "duplicate key" in error_msg or "uq_bed_room_number" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bed number '{payload.bed_number}' already exists in this room."
            )
        raise

@router.patch("/beds/{bed_id}", response_model=BedResponse)
async def update_bed(
    bed_id: str, 
    payload: BedUpdateRequest, 
    db: DBSession, 
    current_user: AdminUser
):
    """Update bed details (status, bed number)."""
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    from app.models.room import Bed, BedStatus
    
    # First, get the bed to check permissions
    result = await db.execute(select(Bed).where(Bed.id == bed_id))
    bed = result.scalar_one_or_none()
    
    if bed is None:
        raise HTTPException(status_code=404, detail="Bed not found.")
    
    # Check hostel access
    bed_hostel_id = str(bed.hostel_id)
    if bed_hostel_id not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied to this bed.")
    
    # If changing bed number, check for duplicates
    if payload.bed_number and payload.bed_number != bed.bed_number:
        # Check if new bed number already exists in same room
        existing = await db.execute(
            select(Bed).where(
                Bed.room_id == bed.room_id,
                Bed.bed_number == payload.bed_number,
                Bed.id != bed_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Bed number '{payload.bed_number}' already exists in this room."
            )
    
    # Handle status update - VALIDATE HERE
    if payload.status is not None:
        # Convert to lowercase for case-insensitive comparison
        status_value = payload.status.lower().strip()
        
        # Map status values
        valid_statuses = {
            "available": BedStatus.AVAILABLE,
            "occupied": BedStatus.OCCUPIED,
            "maintenance": BedStatus.MAINTENANCE,
            "reserved": BedStatus.RESERVED
        }
        
        if status_value in valid_statuses:
            bed.status = valid_statuses[status_value]
        else:
            # Return 400 for invalid status
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: available, occupied, maintenance, reserved. Got: '{payload.status}'"
            )
    
    # Update bed number
    if payload.bed_number:
        bed.bed_number = payload.bed_number
    
    # Handle moving bed to different room
    if payload.room_id is not None and payload.room_id != str(bed.room_id):
        new_room = await db.execute(select(Room).where(Room.id == payload.room_id))
        new_room_obj = new_room.scalar_one_or_none()
        if new_room_obj is None:
            raise HTTPException(status_code=404, detail="Target room not found.")
        
        # Check if bed has active bookings
        from app.models.booking import Booking, BookingStatus
        active_booking = await db.execute(
            select(Booking).where(
                Booking.bed_id == bed_id,
                Booking.status.in_([
                    BookingStatus.APPROVED,
                    BookingStatus.CHECKED_IN,
                    BookingStatus.PENDING_APPROVAL
                ])
            )
        )
        if active_booking.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Cannot move bed with active bookings. Please check-out students first."
            )
        
        bed.room_id = payload.room_id
    
    try:
        await db.commit()
        await db.refresh(bed)
    except IntegrityError as e:
        await db.rollback()
        if "uq_bed_room_number" in str(e):
            raise HTTPException(
                status_code=409,
                detail=f"Bed number '{payload.bed_number or bed.bed_number}' already exists in this room."
            )
        raise HTTPException(status_code=500, detail="Database error occurred.")
    
    return bed


@router.get("/hostels/{hostel_id}/students", response_model=list[StudentResponse])
async def list_students(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).list_students(hostel_id)


@router.patch("/bookings/{booking_id}/approve", response_model=BookingResponse)
async def approve_booking(
    booking_id: str,
    payload: BookingApprovalRequest,
    db: DBSession,
    current_user: AdminUser
):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).approve_booking(
        booking_id=booking_id,
        approved_by=current_user.id,
        bed_id=payload.bed_id,
    )


@router.patch("/bookings/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking_endpoint(
    booking_id: str,
    payload: BookingRejectionRequest,
    db: DBSession,
    current_user: AdminUser
):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).reject_booking(
        booking_id=booking_id,
        rejected_by=current_user.id,
        reason=payload.reason,
    )


@router.patch("/bookings/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: str,
    payload: BookingCancellationRequest,
    db: DBSession,
    current_user: AdminUser
):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).cancel_booking(
        booking_id=booking_id,
        cancelled_by=current_user.id,
        reason=payload.reason,
    )


@router.post("/students/{booking_id}/check-in", response_model=BookingResponse)
async def check_in_student(booking_id: str, db: DBSession, current_user: AdminUser):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    from app.services.student_service import StudentService
    booking = await BookingService(db).check_in_student(booking_id=booking_id, checked_in_by=current_user.id)
    try:
        await db.refresh(booking)
        existing = await StudentService(db).student_repository.get_student_by_booking(str(booking_id))
        if existing is None:
            await StudentService(db).check_in_from_booking(booking_id=booking_id, actor_id=current_user.id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Student record creation failed for booking {booking_id}: {e}")
    return booking


@router.post("/students/{booking_id}/sync-student-record", status_code=200)
async def sync_student_record(booking_id: str, db: DBSession, current_user: AdminUser):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    from app.services.student_service import StudentService
    from app.models.booking import BookingStatus
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != BookingStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail=f"Booking is not checked_in (status: {booking.status})")
    svc = StudentService(db)
    existing = await svc.student_repository.get_student_by_booking(str(booking_id))
    if existing:
        return {"status": "already_exists", "student_id": str(existing.id)}
    student = await svc.check_in_from_booking(booking_id=booking_id, actor_id=current_user.id)
    return {"status": "created", "student_id": str(student.id)}




@router.patch("/students/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    payload: StudentUpdateRequest,
    db: DBSession,
    current_user: AdminUser,
):
    """
    Update student details (updates both users and students tables)
    
    Fields that can be updated:
    - full_name, email, phone, profile_picture_url (from users table)
    - student_number, status, check_in_date, check_out_date (from students table)
    """
    from app.models.student import Student
    from app.models.user import User
    from sqlalchemy import select
    
    # Get the student record
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    
    # Check if admin has access to this student's hostel
    hostel_id = str(student.hostel_id)
    if hostel_id not in current_user.hostel_ids and current_user.role != "super_admin":
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to update this student."
        )
    
    # Get the associated user
    result = await db.execute(
        select(User).where(User.id == student.user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Update users table fields
    updated_user_fields = []
    if payload.full_name is not None:
        user.full_name = payload.full_name
        updated_user_fields.append("full_name")
    if payload.email is not None:
        # Check if email is already taken by another user
        existing = await db.execute(
            select(User).where(
                User.email == payload.email,
                User.id != user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409, 
                detail=f"Email '{payload.email}' is already taken."
            )
        user.email = payload.email
        updated_user_fields.append("email")
    if payload.phone is not None:
        # Check if phone is already taken
        existing = await db.execute(
            select(User).where(
                User.phone == payload.phone,
                User.id != user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409, 
                detail=f"Phone '{payload.phone}' is already taken."
            )
        user.phone = payload.phone
        updated_user_fields.append("phone")

    
    # Update students table fields
    updated_student_fields = []
    if payload.student_number is not None:
        # Check if student number is unique
        existing = await db.execute(
            select(Student).where(
                Student.student_number == payload.student_number,
                Student.id != student.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409, 
                detail=f"Student number '{payload.student_number}' is already taken."
            )
        student.student_number = payload.student_number
        updated_student_fields.append("student_number")
    if payload.status is not None:
        student.status = payload.status
        updated_student_fields.append("status")
    if payload.check_in_date is not None:
        student.check_in_date = payload.check_in_date
        updated_student_fields.append("check_in_date")
    if payload.check_out_date is not None:
        student.check_out_date = payload.check_out_date
        updated_student_fields.append("check_out_date")
    
    # Commit changes
    await db.commit()
    await db.refresh(student)
    await db.refresh(user)
    
    # Build response
    response_data = {
        "id": str(student.id),
        "user_id": str(student.user_id),
        "hostel_id": str(student.hostel_id),
        "student_number": student.student_number,
        "check_in_date": str(student.check_in_date),
        "check_out_date": str(student.check_out_date) if student.check_out_date else None,
        "status": student.status.value if hasattr(student.status, "value") else str(student.status),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "profile_picture_url": user.profile_picture_url,
        "created_at": student.created_at,
        "updated_at": student.updated_at,
    }
    
    # Add room and bed info if available
    if student.room_id:
        from app.models.room import Room
        result = await db.execute(select(Room).where(Room.id == student.room_id))
        room = result.scalar_one_or_none()
        if room:
            response_data["room_number"] = room.room_number
            response_data["room_id"] = str(room.id)
    
    if student.bed_id:
        from app.models.room import Bed
        result = await db.execute(select(Bed).where(Bed.id == student.bed_id))
        bed = result.scalar_one_or_none()
        if bed:
            response_data["bed_number"] = bed.bed_number
            response_data["bed_id"] = str(bed.id)
    
    # Log what was updated
    updated_fields = updated_user_fields + updated_student_fields
    print(f"✓ Student {student_id} updated. Fields changed: {updated_fields}")
    
    return response_data


@router.post("/students/{booking_id}/check-out", response_model=BookingResponse)
async def check_out_student(booking_id: str, db: DBSession, current_user: AdminUser):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).check_out_student(booking_id=booking_id, checked_out_by=current_user.id)


@router.get("/hostels/{hostel_id}/payments", response_model=list[PaymentResponse])

@router.get("/students/{student_id}/payments", response_model=list[PaymentResponse])
async def get_student_payments_admin(
    student_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """
    **Get payment history for a specific student (Admin).**
    
    Requires hostel admin or super admin access to the student's hostel.
    """
    from app.models.student import Student
    from app.services.payment_service import PaymentService
    
    # Get student to verify hostel access
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    
    # Check if admin has access to this student's hostel
    if current_user.role != "super_admin":
        if str(student.hostel_id) not in current_user.hostel_ids:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this student's payment records."
            )
    
    return await PaymentService(db).list_admin_payments(hostel_id=str(student.hostel_id))

async def list_payments(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await PaymentService(db).list_admin_payments(hostel_id=hostel_id)


@router.get("/hostels/{hostel_id}/complaints", response_model=list[ComplaintResponse])
async def list_complaints(
    hostel_id: str,
    db: DBSession,
    current_user: AdminUser,
    priority: str | None = None,
    sla_filter: str | None = Query(None, description="breached | ok"),
):
    _check_hostel(current_user, hostel_id)
    return await ComplaintService(db).list_admin_complaints(
        hostel_id=hostel_id,
        priority=priority,
        sla_filter=sla_filter,
    )


@router.get("/hostels/{hostel_id}/attendance/summary", response_model=list[AttendanceMonthlySummaryItem])
async def attendance_monthly_summary(
    hostel_id: str,
    db: DBSession,
    current_user: AdminUser,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    _check_hostel(current_user, hostel_id)
    return await AttendanceService(db).monthly_attendance_summary(hostel_id=hostel_id, year=year, month=month)


@router.get("/hostels/{hostel_id}/attendance", response_model=list[AttendanceResponse])
async def list_attendance(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AttendanceService(db).list_admin_attendance(hostel_id=hostel_id)


@router.get("/hostels/{hostel_id}/maintenance", response_model=list[MaintenanceResponse])
async def list_maintenance(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await MaintenanceService(db).list_admin_requests(hostel_id=hostel_id)


@router.patch("/maintenance/{request_id}/approve", response_model=MaintenanceResponse)
async def approve_maintenance(request_id: str, db: DBSession, current_user: AdminUser):
    maintenance_hostel_id = await _resolve_maintenance_hostel_id(db, request_id)
    _check_hostel(current_user, maintenance_hostel_id)
    return await MaintenanceService(db).approve_admin_request(actor_id=current_user.id, request_id=request_id)


@router.get("/hostels/{hostel_id}/notices", response_model=list[NoticeResponse])
async def list_notices(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    result = await NoticeService(db).list_admin_notices(hostel_id=hostel_id)
    return result.get("items",[])


@router.get("/hostels/{hostel_id}/notices/read-stats", response_model=list[NoticeReadStatsItem])
async def list_notice_read_stats(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await NoticeService(db).list_notice_read_stats(hostel_id=hostel_id)


@router.post("/hostels/{hostel_id}/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(hostel_id: str, payload: NoticeCreateRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await NoticeService(db).create_admin_notice(actor_id=current_user.id, payload=payload)


@router.get("/hostels/{hostel_id}/mess-menu", response_model=list[MessMenuResponse])
async def list_mess_menu(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await MessMenuService(db).list_admin_menus(hostel_id=hostel_id)


@router.post("/hostels/{hostel_id}/mess-menu", response_model=MessMenuResponse, status_code=201)
async def create_mess_menu(
    hostel_id: str, 
    payload: MessMenuCreateRequest,  # Schema validates first
    db: DBSession, 
    current_user: AdminUser
):
    _check_hostel(current_user, hostel_id)
    try:
        return await MessMenuService(db).create_admin_menu(
            actor_id=current_user.id, 
            hostel_id=hostel_id, 
            payload=payload
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/hostels/{hostel_id}/supervisors", response_model=list[SupervisorResponse])
async def list_supervisors(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).list_supervisors(hostel_id)


@router.post("/hostels/{hostel_id}/supervisors", response_model=SupervisorResponse, status_code=201)
async def create_supervisor(hostel_id: str, payload: SupervisorCreateRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).create_supervisor(hostel_id, current_user.id, payload)


@router.post("/hostels/{hostel_id}/students/direct", response_model=DirectStudentAddResponse, status_code=201)
async def add_student_direct(hostel_id: str, payload: DirectStudentAddRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).add_student_direct(hostel_id, current_user.id, payload)


@router.patch("/hostels/{hostel_id}/complaints/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    hostel_id: str,
    complaint_id: str,
    payload: ComplaintUpdateRequest,
    db: DBSession,
    current_user: AdminUser
):
    complaint_hostel_id = await _resolve_complaint_hostel_id(db, complaint_id)
    _check_hostel(current_user, complaint_hostel_id)
    if complaint_hostel_id != hostel_id:
        raise HTTPException(status_code=400, detail="Complaint does not belong to the specified hostel.")
    return await ComplaintService(db).update_admin_complaint(hostel_id=hostel_id, complaint_id=complaint_id, payload=payload)

@router.get("/hostels/{hostel_id}/notices/paginated")
async def list_notices_paginated(
    hostel_id: str,
    db: DBSession,
    current_user: AdminUser,
    page: int = 1,
    per_page: int = 20,
    is_published: bool | None = None,
    notice_type: str | None = None,
):
    """List notices with pagination and filters"""
    _check_hostel(current_user, hostel_id)
    return await NoticeService(db).list_admin_notices(
        hostel_id=hostel_id,
        page=page,
        per_page=per_page,
        is_published=is_published,
        notice_type=notice_type,
    )


@router.get("/notices/platform", response_model=dict)
async def list_platform_notices(
    db: DBSession,
    current_user: AdminUser,
    page: int = 1,
    per_page: int = 20,
    is_published: bool | None = None,
):
    """List platform-wide notices (hostel_id = null)"""
    return await NoticeService(db).list_admin_notices(
        hostel_id=None,
        page=page,
        per_page=per_page,
        is_published=is_published,
    )


@router.get("/notices/{notice_id}")
async def get_notice(
    notice_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Get a single notice by ID"""
    notice = await NoticeService(db).get_notice_by_id(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found.")
    
    return {
        "id": str(notice.id),
        "hostel_id": str(notice.hostel_id) if notice.hostel_id else None,
        "title": notice.title,
        "content": notice.content,
        "notice_type": notice.notice_type,
        "priority": notice.priority,
        "is_published": notice.is_published,
        "publish_at": notice.publish_at,
        "expires_at": notice.expires_at,
        "created_by": str(notice.created_by),
        "created_at": notice.created_at,
        "updated_at": notice.updated_at,
    }


@router.post("/hostels/{hostel_id}/notices", status_code=201)
async def create_admin_notice(
    hostel_id: str,
    payload: NoticeCreateRequest,
    db: DBSession,
    current_user: AdminUser,
):
    """Create a notice for a specific hostel"""
    _check_hostel(current_user, hostel_id)
    payload.hostel_id = hostel_id
    notice = await NoticeService(db).create_admin_notice(
        actor_id=current_user.id,
        payload=payload,  
    )
    return {
        "id": str(notice.id),
        "hostel_id": str(notice.hostel_id) if notice.hostel_id else None,
        "title": notice.title,
        "content": notice.content,
        "notice_type": notice.notice_type,
        "priority": notice.priority,
        "is_published": notice.is_published,
        "created_at": notice.created_at,
    }


@router.post("/notices/platform", status_code=201)
async def create_platform_notice(
    payload: NoticeCreateRequest,
    db: DBSession,
    current_user: AdminUser,
):
    """Create a platform-wide notice (visible to all hostels)"""
    payload.hostel_id = None
    notice = await NoticeService(db).create_admin_notice(
        actor_id=current_user.id,
        payload=payload,
    )
    return {
        "id": str(notice.id),
        "hostel_id": None,
        "title": notice.title,
        "content": notice.content,
        "notice_type": notice.notice_type,
        "priority": notice.priority,
        "is_published": notice.is_published,
        "created_at": notice.created_at,
    }


@router.patch("/notices/{notice_id}")
async def update_notice(
    notice_id: str,
    payload: NoticeUpdateRequest,
    db: DBSession,
    current_user: AdminUser,
):
    """Update a notice"""
    notice = await NoticeService(db).update_notice(
        notice_id=notice_id,
        payload=payload,
    )
    return {
        "id": str(notice.id),
        "title": notice.title,
        "content": notice.content,
        "notice_type": notice.notice_type,
        "priority": notice.priority,
        "is_published": notice.is_published,
        "updated_at": notice.updated_at,
    }


@router.patch("/notices/{notice_id}/toggle-publish")
async def toggle_notice_publish(
    notice_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Toggle notice published status"""
    notice = await NoticeService(db).toggle_publish_status(
        notice_id=notice_id,
    )
    return {
        "id": str(notice.id),
        "is_published": notice.is_published,
    }


@router.delete("/notices/{notice_id}", status_code=204)
async def delete_notice(
    notice_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Delete a notice"""
    await NoticeService(db).delete_notice(notice_id=notice_id)
    return Response(status_code=204)

@router.get("/students/{student_id}/complete", response_model=CompleteStudentDetailResponse)
async def get_complete_student_details(
    student_id: str,
    db: DBSession,
    current_user: Annotated[CurrentUser, Depends(require_roles("hostel_admin", "super_admin"))],
):
    """
    Get complete student details including:
    - Personal info (name, email, phone, gender, DOB)
    - Student info (student number, status, dates)
    - Room & Bed info (room number, bed number, room type, floor)
    - Payment info (payment status, amount paid, due date)
    - Hostel info (hostel name, city, type)
    - Booking info (booking number, booking mode)
    
    Accessible by: super_admin, hostel_admin (with hostel access)
    """
    # For super_admin, bypass hostel check
    if current_user.role == "super_admin":
        student = await AdminService(db).get_complete_student_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")
        return student
    
    # For hostel_admin, check hostel access
    student_with_hostel = await AdminService(db).get_student_with_hostel_id(student_id)
    if not student_with_hostel:
        raise HTTPException(status_code=404, detail="Student not found.")
    
    hostel_id = student_with_hostel.get("hostel_id")
    if hostel_id not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied to this student.")
    
    return await AdminService(db).get_complete_student_by_id(student_id)

@router.delete("/mess-menu/{item_id}", status_code=204)
async def delete_mess_menu_item(
    item_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Delete a specific mess menu item."""
    await MessMenuService(db).delete_menu_item(
        actor_id=current_user.id,
        item_id=item_id,
    )
    return Response(status_code=204)

@router.get("/supervisors/{supervisor_id}", response_model=SupervisorResponse)
async def get_supervisor(
    supervisor_id: str,
    db: DBSession,
    current_user: AdminUser
):
    """Get a specific supervisor by ID"""
    supervisor = await AdminService(db).get_supervisor_by_id(supervisor_id)
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor not found.")
    
    # Check if supervisor belongs to admin's hostels
    from sqlalchemy import select
    from app.models.hostel import SupervisorHostelMapping
    result = await db.execute(
        select(SupervisorHostelMapping.hostel_id).where(
            SupervisorHostelMapping.supervisor_id == supervisor_id
        )
    )
    supervisor_hostel_ids = {str(hid) for hid in result.scalars().all()}
    
    if not supervisor_hostel_ids.intersection(current_user.hostel_ids):
        raise HTTPException(
            status_code=403, 
            detail="You don't have access to this supervisor."
        )
    
    return supervisor


@router.patch("/supervisors/{supervisor_id}", response_model=SupervisorResponse)
async def update_supervisor(
    supervisor_id: str,
    payload: SupervisorUpdateRequest,
    db: DBSession,
    current_user: AdminUser
):
    return await AdminService(db).update_supervisor(
        supervisor_id=supervisor_id,
        payload=payload,
        admin_hostel_ids=current_user.hostel_ids
    )


@router.delete("/supervisors/{supervisor_id}", status_code=204)
async def delete_supervisor(
    supervisor_id: str,
    db: DBSession,
    current_user: AdminUser
):

    await AdminService(db).delete_supervisor(
        supervisor_id=supervisor_id,
        admin_hostel_ids=current_user.hostel_ids
    )
    return Response(status_code=204)


@router.delete("/complaints/{complaint_id}", status_code=204)
async def delete_complaint(
    complaint_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Delete a complaint - Admin only"""
    # Get complaint to check hostel access
    from app.models.operations import Complaint
    
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    
    # Check if admin has access to this hostel
    if str(complaint.hostel_id) not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied to this complaint.")
    
    # Delete the complaint
    await db.delete(complaint)
    await db.commit()
    
    return Response(status_code=204)

@router.delete("/complaints/{complaint_id}", status_code=204)
async def delete_complaint(
    complaint_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    
    # Get the complaint
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found."
        )
    
    # Check if admin has access to this hostel
    if str(complaint.hostel_id) not in current_user.hostel_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this complaint."
        )
    
    # Delete the complaint
    await db.delete(complaint)
    await db.commit()
    
    return Response(status_code=204)

@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """
    Hard delete a student. 
    Warning: Unlinks payments and bookings, and deletes all linked attendance/complaint records.
    """
    from app.models.student import Student
    from sqlalchemy import select
    
    # Check if admin has access to this student's hostel
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
        
    if str(student.hostel_id) not in current_user.hostel_ids and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You don't have permission to delete this student.")
        
    await AdminService(db).delete_student(student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Get student details by ID"""
    from app.models.student import Student
    from app.models.user import User
    from app.models.room import Room, Bed
    from app.models.booking import Booking
    from sqlalchemy import select
    
    # Get student with all related data
    result = await db.execute(
        select(Student, User, Room, Bed, Booking)
        .join(User, User.id == Student.user_id)
        .join(Room, Room.id == Student.room_id)
        .join(Bed, Bed.id == Student.bed_id)
        .join(Booking, Booking.id == Student.booking_id)
        .where(Student.id == student_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Student not found.")
    
    student, user, room, bed, booking = row
    
    # Check permission
    if str(student.hostel_id) not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied to this student.")
    
    return {
        "id": str(student.id),
        "user_id": str(student.user_id),
        "hostel_id": str(student.hostel_id),
        "room_id": str(student.room_id),
        "bed_id": str(student.bed_id),
        "booking_id": str(student.booking_id),
        "student_number": student.student_number,
        "check_in_date": str(student.check_in_date),
        "check_out_date": str(student.check_out_date) if student.check_out_date else None,
        "status": student.status.value if hasattr(student.status, "value") else str(student.status),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "profile_picture_url": user.profile_picture_url,
        "room_number": room.room_number,
        "bed_number": bed.bed_number,
        "booking_number": booking.booking_number,
        "created_at": student.created_at,
        "updated_at": student.updated_at,
    }


@router.patch("/students/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    db: DBSession,
    current_user: AdminUser,
    check_out_date: str | None = None,
    status: str | None = None,
):
    """Update student (check-out date, status, etc.)"""
    from app.models.student import Student
    from app.models.booking import Booking, BookingStatus
    from app.models.room import Bed, BedStatus
    from sqlalchemy import select
    from datetime import date
    
    # Get student
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    
    # Check permission
    if str(student.hostel_id) not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    # Update check_out_date
    if check_out_date:
        student.check_out_date = date.fromisoformat(check_out_date)
        student.status = "CHECKED_OUT"
        
        # Update booking status
        booking_result = await db.execute(
            select(Booking).where(Booking.id == student.booking_id)
        )
        booking = booking_result.scalar_one_or_none()
        if booking:
            booking.status = BookingStatus.CHECKED_OUT
        
        # Free up the bed
        bed_result = await db.execute(
            select(Bed).where(Bed.id == student.bed_id)
        )
        bed = bed_result.scalar_one_or_none()
        if bed:
            bed.status = BedStatus.AVAILABLE
    
    # Update status
    if status:
        student.status = status
    
    await db.commit()
    await db.refresh(student)
    
    return student

# Add these mess menu item endpoints

@router.get("/mess-menu/{item_id}")
async def get_mess_menu_item(
    item_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Get a single mess menu item by ID"""
    from app.models.operations import MessMenuItem, MessMenu
    
    result = await db.execute(
        select(MessMenuItem, MessMenu)
        .join(MessMenu, MessMenu.id == MessMenuItem.menu_id)
        .where(MessMenuItem.id == item_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Mess menu item not found.")
    
    item, menu = row
    
    # Check permission
    if str(menu.hostel_id) not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied to this hostel.")
    
    return {
        "id": str(item.id),
        "menu_id": str(item.menu_id),
        "hostel_id": str(menu.hostel_id),
        "day_of_week": item.day_of_week,
        "meal_type": item.meal_type,
        "item_name": item.item_name,
        "is_veg": item.is_veg,
        "special_note": item.special_note,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.patch("/mess-menu/{item_id}")
async def update_mess_menu_item(
    item_id: str,
    db: DBSession,
    request: Request,
    current_user: AdminUser,
):
    """Update a mess menu item with proper validation."""
    body = await request.json()
    
    # Manual validation
    if "meal_type" in body:
        meal_type = body["meal_type"].strip().lower()
        valid_meal_types = ["breakfast", "lunch", "snacks", "dinner"]
        if meal_type not in valid_meal_types:
            raise HTTPException(
                status_code=400,
                detail=f"meal_type must be one of: {', '.join(valid_meal_types)}"
            )
        body["meal_type"] = meal_type
    
    if "day_of_week" in body:
        day_of_week = body["day_of_week"].strip().capitalize()
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if day_of_week not in valid_days:
            raise HTTPException(
                status_code=400,
                detail=f"day_of_week must be one of: {', '.join(valid_days)}"
            )
        body["day_of_week"] = day_of_week
    
    # Continue with update...
    from app.models.operations import MessMenuItem, MessMenu
    result = await db.execute(
        select(MessMenuItem, MessMenu)
        .join(MessMenu, MessMenu.id == MessMenuItem.menu_id)
        .where(MessMenuItem.id == item_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Mess menu item not found.")
    
    item, menu = row
    
    if str(menu.hostel_id) not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    # Apply updates
    if "item_name" in body:
        item.item_name = body["item_name"]
    if "is_veg" in body:
        item.is_veg = body["is_veg"]
    if "special_note" in body:
        item.special_note = body["special_note"]
    if "meal_type" in body:
        item.meal_type = body["meal_type"]
    if "day_of_week" in body:
        item.day_of_week = body["day_of_week"]
    
    await db.commit()
    await db.refresh(item)
    
    return {
        "id": str(item.id),
        "item_name": item.item_name,
        "is_veg": item.is_veg,
        "special_note": item.special_note,
        "meal_type": item.meal_type,
        "day_of_week": item.day_of_week,
        "updated_at": item.updated_at,
    }

@router.delete("/mess-menu/{item_id}", status_code=204)
async def delete_mess_menu_item(
    item_id: str,
    db: DBSession,
    current_user: AdminUser,
):
    """Delete a mess menu item"""
    from app.models.operations import MessMenuItem, MessMenu
    from sqlalchemy import select
    
    result = await db.execute(
        select(MessMenuItem, MessMenu)
        .join(MessMenu, MessMenu.id == MessMenuItem.menu_id)
        .where(MessMenuItem.id == item_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Mess menu item not found.")
    
    item, menu = row
    
    # Check permission
    if str(menu.hostel_id) not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    await db.delete(item)
    await db.commit()
    
    return Response(status_code=204)

@router.get("/rooms/{room_id}/beds/count")
async def get_room_bed_stats(room_id: str, db: DBSession, current_user: AdminUser):
    """Get bed statistics for a room."""
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    
    from sqlalchemy import select, func
    from app.models.room import Bed
    
    # Get total beds count
    total_result = await db.execute(
        select(func.count()).select_from(Bed).where(Bed.room_id == room_id)
    )
    total_beds = total_result.scalar() or 0
    
    # Get bed counts by status
    status_counts = await db.execute(
        select(Bed.status, func.count())
        .where(Bed.room_id == room_id)
        .group_by(Bed.status)
    )
    
    return {
        "room_id": room_id,
        "total_beds": total_beds,
        "status_counts": {status.value: count for status, count in status_counts.all()},
        "capacity": None  # Will be filled by caller
    }

@router.get("/rooms/{room_id}/beds/stats")
async def get_room_bed_stats(room_id: str, db: DBSession, current_user: AdminUser):
    """Get bed statistics for a room."""
    from sqlalchemy import select, func
    from app.models.room import Bed
    
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    
    # Get total beds
    total_result = await db.execute(
        select(func.count()).select_from(Bed).where(Bed.room_id == room_id)
    )
    total_beds = total_result.scalar() or 0
    
    # Get counts by status
    status_counts = await db.execute(
        select(Bed.status, func.count())
        .where(Bed.room_id == room_id)
        .group_by(Bed.status)
    )
    
    return {
        "room_id": room_id,
        "total_beds": total_beds,
        "status_counts": {status.value: count for status, count in status_counts.all()}
    }
    
@router.patch("/maintenance/{request_id}", response_model=MaintenanceResponse)
async def update_maintenance_request_admin(
    request_id: str,
    payload: MaintenanceUpdateRequest,
    db: DBSession,
    current_user: AdminUser
):
    """
    Update a maintenance request as admin.
    Admins can approve requests (change from pending_approval to approved)
    or update any request in their hostel.
    """
    maintenance_hostel_id = await _resolve_maintenance_hostel_id(db, request_id)
    _check_hostel(current_user, maintenance_hostel_id)
    
    return await MaintenanceService(db).update_admin_request(
        admin_id=current_user.id,
        request_id=request_id,
        payload=payload
    )

@router.get("/profile", response_model=AdminProfileResponse)
async def get_admin_profile(
    current_user: AdminUser,
    db: DBSession,
):
    """
    **Get admin profile information.**
    
    Returns personal details including name, email, phone, and assigned hostels.
    """
    from app.models.user import User
    from app.models.hostel import AdminHostelMapping, Hostel
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Get assigned hostels with details
    hostel_result = await db.execute(
        select(Hostel.id, Hostel.name, Hostel.city, Hostel.status, AdminHostelMapping.is_primary)
        .join(AdminHostelMapping, AdminHostelMapping.hostel_id == Hostel.id)
        .where(AdminHostelMapping.admin_id == current_user.id)
    )
    assigned_hostels = [
        {
            "id": str(row.id),
            "name": row.name,
            "city": row.city,
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
            "is_primary": row.is_primary
        }
        for row in hostel_result.all()
    ]
    
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "profile_picture_url": user.profile_picture_url,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "is_phone_verified": user.is_phone_verified,
        "assigned_hostels": assigned_hostels,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.patch("/profile", response_model=AdminProfileResponse)
async def update_admin_profile(
    request: Request,  # Change to use Request to get raw body
    current_user: AdminUser,
    db: DBSession,
):
    """
    **Update admin profile.**
    
    Can update: full_name, phone, profile_picture_url.
    Email cannot be changed by admin (requires super admin action).
    """
    from app.models.user import User
    from sqlalchemy import select
    
    # Parse body
    try:
        body = await request.json()
    except:
        body = {}
    
    # If empty body, just return current profile
    if not body:
        result = await db.execute(
            select(User).where(User.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        # Get assigned hostels for response
        from app.models.hostel import AdminHostelMapping, Hostel
        hostel_result = await db.execute(
            select(Hostel.id, Hostel.name, Hostel.city, Hostel.status, AdminHostelMapping.is_primary)
            .join(AdminHostelMapping, AdminHostelMapping.hostel_id == Hostel.id)
            .where(AdminHostelMapping.admin_id == current_user.id)
        )
        assigned_hostels = [
            {
                "id": str(row.id),
                "name": row.name,
                "city": row.city,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "is_primary": row.is_primary
            }
            for row in hostel_result.all()
        ]
        
        return {
            "id": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "profile_picture_url": user.profile_picture_url,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "is_phone_verified": user.is_phone_verified,
            "assigned_hostels": assigned_hostels,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
    
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Update full name
    if "full_name" in body and body["full_name"] is not None:
        user.full_name = body["full_name"]
    
    # Update phone (check uniqueness)
    if "phone" in body and body["phone"] is not None:
        phone = body["phone"]
        
        # Validate phone format
        import re
        # Remove any non-digit characters for validation
        digits_only = re.sub(r'[^0-9]', '', phone)
        
        # Check length - should be 10-13 digits after cleaning
        if len(digits_only) < 10 or len(digits_only) > 13:
            raise HTTPException(
                status_code=400,
                detail="Phone number must have between 10 and 13 digits."
            )
        
        # For Indian numbers, first digit should be 6-9 if exactly 10 digits
        if len(digits_only) == 10 and digits_only[0] not in ['6', '7', '8', '9']:
            raise HTTPException(
                status_code=400,
                detail="Indian phone number must start with 6, 7, 8, or 9."
            )
        
        # Check if phone already taken by another user
        existing = await db.execute(
            select(User).where(
                User.phone == phone,
                User.id != current_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Phone number already registered by another user."
            )
        user.phone = phone
    
    # Update profile picture

    
    await db.commit()
    await db.refresh(user)
    
    # Get assigned hostels for response
    from app.models.hostel import AdminHostelMapping, Hostel
    hostel_result = await db.execute(
        select(Hostel.id, Hostel.name, Hostel.city, Hostel.status, AdminHostelMapping.is_primary)
        .join(AdminHostelMapping, AdminHostelMapping.hostel_id == Hostel.id)
        .where(AdminHostelMapping.admin_id == current_user.id)
    )
    assigned_hostels = [
        {
            "id": str(row.id),
            "name": row.name,
            "city": row.city,
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
            "is_primary": row.is_primary
        }
        for row in hostel_result.all()
    ]
    
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "profile_picture_url": user.profile_picture_url,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "is_phone_verified": user.is_phone_verified,
        "assigned_hostels": assigned_hostels,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

@router.post("/change-password")
async def change_admin_password(
    request: Request,  # Add this to get raw body
    current_user: AdminUser,
    db: DBSession
):
    """
    **Change admin password.**
    
    Requirements:
    - Current password must be correct
    - New password: min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char
    - New password and confirm password must match
    
    After successful change, all other sessions are revoked for security.
    """
    from app.models.user import User
    from sqlalchemy import select
    
    # Parse body manually to avoid Pydantic validation
    body = await request.json()
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")
    confirm_password = body.get("confirm_password", "")
    
    # Validate passwords match FIRST
    if new_password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="New passwords do not match."
        )
    
    # Validate new password strength BEFORE any other operations
    errors = []
    if len(new_password) < 8:
        errors.append("Password must be at least 8 characters")
    if not re.search(r'[A-Z]', new_password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', new_password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r'[0-9]', new_password):
        errors.append("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        errors.append("Password must contain at least one special character")
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail="; ".join(errors)
        )
    
    # Get the user record
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Verify current password
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect."
        )
    
    # Hash and update password
    user.password_hash = hash_password(new_password)
    
    # Revoke all other sessions for security (keep current)
    repo = UserRepository(db)
    await repo.revoke_all_refresh_tokens(
        user_id=current_user.id,
        revoked_at=datetime.now(UTC)
    )
    
    await db.commit()
    
    return {
        "message": "Password changed successfully.",
        "user_id": str(user.id)
    }