# app/api/v1/supervisor/routes.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import Response
from typing import Optional
from uuid import UUID
from sqlalchemy import select, or_, func, desc
from app.models.user import User
from pydantic import BaseModel, Field, model_validator
import re
from datetime import UTC, datetime
from app.core.security import verify_password, hash_password
from app.repositories.user_repository import UserRepository
from pydantic import ValidationError as PydanticValidationError
import re
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status  
from app.dependencies import CurrentUser, require_roles
from app.dependencies import DBSession
from app.schemas.attendance import AttendanceCreateRequest, AttendanceResponse
from app.schemas.complaint import ComplaintResponse, ComplaintUpdateRequest
from app.schemas.maintenance import MaintenanceCreateRequest, MaintenanceResponse, MaintenanceUpdateRequest
from app.schemas.mess_menu import MessMenuResponse
from app.schemas.notice import NoticeCreateRequest, NoticeUpdateRequest, NoticeResponse  # ADD THIS LINE
from app.schemas.student import StudentResponse
from app.services.admin_service import AdminService
from app.services.attendance_service import AttendanceService
from app.services.complaint_service import ComplaintService
from app.models.operations import Complaint
from app.services.maintenance_service import MaintenanceService
from app.services.mess_menu_service import MessMenuService
from app.services.notice_service import NoticeService
from app.services.supervisor_service import SupervisorDashboardResponse, SupervisorService
from pydantic import BaseModel, Field
from app.core.security import verify_password, hash_password

router = APIRouter()
SupervisorUser = Annotated[CurrentUser, Depends(require_roles("supervisor"))]

class SupervisorChangePasswordRequest(BaseModel):
    """Request to change supervisor password"""
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    
class SupervisorProfileResponse(BaseModel):
    """Supervisor profile response model"""
    id: str
    email: str
    phone: str
    full_name: str
    role: str
    profile_picture_url: str | None = None
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime
    updated_at: datetime

class SupervisorProfileUpdateRequest(BaseModel):
    """Request to update supervisor profile"""
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=8, max_length=30)
    profile_picture_url: str | None = None

class SupervisorChangePasswordRequest(BaseModel):
    """Request to change supervisor password"""
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)



@router.get("/dashboard", response_model=SupervisorDashboardResponse)
async def dashboard(current_user: SupervisorUser, db: DBSession):
    """**Supervisor dashboard** — students, complaints, attendance, maintenance counts for assigned hostel."""
    return await SupervisorService(db).get_dashboard(current_user.id)

@router.get("/students", response_model=list[StudentResponse])
async def students(current_user: SupervisorUser, db: DBSession):
    """**List students in the supervisor's assigned hostel.**"""
    try:
        hostel_ids = list(current_user.hostel_ids)
        if not hostel_ids:
            return []
        
        # Use AdminService which now includes gender
        admin_service = AdminService(db)
        students_data = await admin_service.list_students_for_hostels(hostel_ids)
        
        # Log for debugging
        print(f"Supervisor students: found {len(students_data)} students")
        if students_data:
            print(f"Sample student gender: {students_data[0].get('gender', 'NOT FOUND')}")
        
        return students_data
    except Exception as e:
        print(f"Error in supervisor students endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/complaints", response_model=list[ComplaintResponse])
async def complaints(current_user: SupervisorUser, db: DBSession):
    """**List complaints assigned to or visible by this supervisor.**"""
    return await ComplaintService(db).list_supervisor_complaints(supervisor_id=current_user.id)


@router.patch("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(complaint_id: str, payload: ComplaintUpdateRequest, current_user: SupervisorUser, db: DBSession):
    """**Update complaint** — change status, add resolution notes."""
    return await ComplaintService(db).update_supervisor_complaint(
        supervisor_id=current_user.id, complaint_id=complaint_id, payload=payload,
    )


@router.get("/attendance", response_model=list[AttendanceResponse])
async def attendance(current_user: SupervisorUser, db: DBSession):
    """**List attendance records** for the supervisor's hostel."""
    return await AttendanceService(db).list_supervisor_attendance(supervisor_id=current_user.id)


@router.post("/attendance", response_model=AttendanceResponse, status_code=201)
async def mark_attendance(payload: AttendanceCreateRequest, current_user: SupervisorUser, db: DBSession):
    """
    **Mark attendance for a student.**

    - One record per student per day (enforced by DB unique constraint)
    - `status`: `present`, `absent`, `late`, `on_leave`
    - `method`: `manual`, `biometric` (biometric is phase 2)
    """
    return await AttendanceService(db).create_supervisor_attendance(
        supervisor_id=current_user.id, payload=payload,
    )


@router.get("/maintenance", response_model=list[MaintenanceResponse])
async def maintenance(current_user: SupervisorUser, db: DBSession):
    """**List maintenance requests** created by or visible to this supervisor."""
    return await MaintenanceService(db).list_supervisor_requests(supervisor_id=current_user.id)


@router.post("/maintenance", response_model=MaintenanceResponse, status_code=201)
async def create_maintenance(payload: MaintenanceCreateRequest, current_user: SupervisorUser, db: DBSession):
    """
    **Create a maintenance request.**

    If `requires_admin_approval` is true, the request will appear in the
    admin's maintenance queue for sign-off before work begins.
    """
    return await MaintenanceService(db).create_supervisor_request(
        supervisor_id=current_user.id, payload=payload,
    )


@router.patch("/maintenance/{request_id}", response_model=MaintenanceResponse)
async def update_maintenance(
    request_id: str, 
    payload: MaintenanceUpdateRequest, 
    current_user: SupervisorUser, 
    db: DBSession
):
    """**Update maintenance request** — status, vendor info, actual cost."""
    
    # Validate status before passing to service
    if payload.status is not None:
        valid_statuses = ["open", "in_progress", "completed", "cancelled", "approved"]
        status_value = payload.status.lower().strip()
        
        if status_value not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}. Got: '{payload.status}'"
            )
    
    return await MaintenanceService(db).update_supervisor_request(
        supervisor_id=current_user.id, 
        request_id=request_id, 
        payload=payload,
    )


@router.get("/notices")
async def notices(current_user: SupervisorUser,db: DBSession,page: int = 1,per_page: int = 20,is_published: bool | None = None,):
    """**List notices** for the supervisor's hostel with pagination."""
    result = await NoticeService(db).list_supervisor_notices(supervisor_id=current_user.id,page=page,per_page=per_page,is_published=is_published,)
    return result

@router.post("/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(payload: NoticeCreateRequest, current_user: SupervisorUser, db: DBSession):
    """**Create a notice** for the hostel. Visible to all students in the hostel."""
    return await NoticeService(db).create_supervisor_notice(actor_id=current_user.id, payload=payload)


@router.get("/mess-menu", response_model=list[MessMenuResponse])
async def mess_menu(current_user: SupervisorUser, db: DBSession):
    """**View weekly mess menus** for the supervisor's hostel."""
    return await MessMenuService(db).list_supervisor_menus(supervisor_id=current_user.id)


# ==================== NOTICE MANAGEMENT ROUTES ====================


def is_valid_uuid(uuid_string: str) -> bool:
    """Check if string is valid UUID"""
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False

@router.get("/notices/paginated")
async def list_supervisor_notices_paginated(
    db: DBSession,
    current_user: SupervisorUser,
    page: int = 1,
    per_page: int = 20,
    is_published: Optional[bool] = None,
):
    """List notices with pagination for supervisor"""
    # Get supervisor's hostel IDs
    from app.models.hostel import SupervisorHostelMapping
    
    result = await db.execute(
        select(SupervisorHostelMapping.hostel_id).where(
            SupervisorHostelMapping.supervisor_id == current_user.id
        )
    )
    hostel_ids = [str(hid) for hid in result.scalars().all()]
    
    if not hostel_ids:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}
    
    # Build query
    from app.models.operations import Notice
    query = select(Notice).where(
        or_(
            Notice.hostel_id.in_(hostel_ids),
            Notice.hostel_id.is_(None)
        )
    )
    
    if is_published is not None:
        query = query.where(Notice.is_published == is_published)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = int(total_result.scalar() or 0)
    
    # Get paginated results
    query = query.order_by(desc(Notice.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    notices = list(result.scalars().all())
    
    items = []
    for notice in notices:
        items.append({
            "id": str(notice.id),
            "hostel_id": str(notice.hostel_id) if notice.hostel_id else None,
            "title": notice.title,
            "content": notice.content,
            "notice_type": notice.notice_type,
            "priority": notice.priority,
            "is_published": notice.is_published,
            "created_at": notice.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.patch("/notices/{notice_id}")
async def update_supervisor_notice(
    notice_id: str,
    payload: NoticeUpdateRequest,
    db: DBSession,
    current_user: SupervisorUser,
):
    """Update a notice - FIXED VERSION"""
    from app.models.operations import Notice
    from app.models.hostel import SupervisorHostelMapping
    
    # Get the notice
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found.")
    
    # Get supervisor's hostel IDs
    mapping_result = await db.execute(
        select(SupervisorHostelMapping.hostel_id).where(
            SupervisorHostelMapping.supervisor_id == current_user.id
        )
    )
    supervisor_hostel_ids = [str(hid) for hid in mapping_result.scalars().all()]
    
    print(f"DEBUG: Supervisor ID: {current_user.id}")
    print(f"DEBUG: Supervisor hostel IDs: {supervisor_hostel_ids}")
    print(f"DEBUG: Notice hostel ID: {notice.hostel_id}")
    
    # Permission check - platform notices (hostel_id = None) can't be edited by supervisor
    if notice.hostel_id is None:
        raise HTTPException(
            status_code=403, 
            detail="Platform-wide notices can only be edited by Admin or Super Admin."
        )
    
    # Check if notice belongs to supervisor's hostel
    notice_hostel_str = str(notice.hostel_id)
    if notice_hostel_str not in supervisor_hostel_ids:
        raise HTTPException(
            status_code=403, 
            detail=f"You don't have permission to update this notice. Notice belongs to hostel {notice_hostel_str}, you have access to {supervisor_hostel_ids}"
        )
    
    # Update notice
    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notice, field, value)
    
    await db.commit()
    await db.refresh(notice)
    
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
async def toggle_supervisor_notice_publish(
    notice_id: str,
    db: DBSession,
    current_user: SupervisorUser,
):
    """Toggle notice published status - FIXED VERSION"""
    from app.models.operations import Notice
    from app.models.hostel import SupervisorHostelMapping
    
    # Get the notice
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found.")
    
    # Get supervisor's hostel IDs
    mapping_result = await db.execute(
        select(SupervisorHostelMapping.hostel_id).where(
            SupervisorHostelMapping.supervisor_id == current_user.id
        )
    )
    supervisor_hostel_ids = [str(hid) for hid in mapping_result.scalars().all()]
    
    # Permission check
    if notice.hostel_id is None:
        raise HTTPException(
            status_code=403, 
            detail="Platform-wide notices can only be toggled by Admin or Super Admin."
        )
    
    notice_hostel_str = str(notice.hostel_id)
    if notice_hostel_str not in supervisor_hostel_ids:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to modify this notice."
        )
    
    # Toggle publish status
    notice.is_published = not notice.is_published
    await db.commit()
    await db.refresh(notice)
    
    return {
        "id": str(notice.id),
        "is_published": notice.is_published,
    }


@router.delete("/notices/{notice_id}", status_code=204)
async def delete_supervisor_notice(
    notice_id: str,
    db: DBSession,
    current_user: SupervisorUser,
):
    """Delete a notice - FIXED VERSION"""
    from app.models.operations import Notice
    from app.models.hostel import SupervisorHostelMapping
    
    # Get the notice
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found.")
    
    # Get supervisor's hostel IDs
    mapping_result = await db.execute(
        select(SupervisorHostelMapping.hostel_id).where(
            SupervisorHostelMapping.supervisor_id == current_user.id
        )
    )
    supervisor_hostel_ids = [str(hid) for hid in mapping_result.scalars().all()]
    
    # Permission check
    if notice.hostel_id is None:
        raise HTTPException(
            status_code=403, 
            detail="Platform-wide notices can only be deleted by Admin or Super Admin."
        )
    
    notice_hostel_str = str(notice.hostel_id)
    if notice_hostel_str not in supervisor_hostel_ids:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to delete this notice."
        )
    # Get supervisor's hostel IDs
    mapping_result = await db.execute(
        select(SupervisorHostelMapping.hostel_id).where(
            SupervisorHostelMapping.supervisor_id == current_user.id
        )
    )
    supervisor_hostel_ids = [str(hid) for hid in mapping_result.scalars().all()]
    
    # Permission check
    if notice.hostel_id is None:
        raise HTTPException(
            status_code=403, 
            detail="Platform-wide notices can only be deleted by Admin or Super Admin."
        )
    
    notice_hostel_str = str(notice.hostel_id)
    if notice_hostel_str not in supervisor_hostel_ids:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to delete this notice."
        )
    
    await db.delete(notice)
    await db.commit()
    return Response(status_code=204)

@router.delete("/complaints/{complaint_id}", status_code=204)
async def delete_complaint(
    complaint_id: str,
    db: DBSession,
    current_user: SupervisorUser,
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

@router.post("/change-password")
async def change_supervisor_password(
    request: Request,  # Add this to get raw body
    current_user: SupervisorUser,
    db: DBSession
):
    """
    **Change supervisor password.**
    
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


@router.get("/profile", response_model=SupervisorProfileResponse)
async def get_supervisor_profile(
    current_user: SupervisorUser,
    db: DBSession,
):
    """
    **Get supervisor profile information.**
    
    Returns personal details including name, email, phone, and assigned hostels.
    """
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Get assigned hostels for display
    from app.models.hostel import SupervisorHostelMapping, Hostel
    hostel_result = await db.execute(
        select(Hostel.name)
        .join(SupervisorHostelMapping, SupervisorHostelMapping.hostel_id == Hostel.id)
        .where(SupervisorHostelMapping.supervisor_id == current_user.id)
    )
    assigned_hostels = [row[0] for row in hostel_result.all()]
    
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
        "assigned_hostels": assigned_hostels,  # Extra field for UI
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.patch("/profile", response_model=SupervisorProfileResponse)
async def update_supervisor_profile(
    payload: SupervisorProfileUpdateRequest,
    current_user: SupervisorUser,
    db: DBSession,
):
    """
    **Update supervisor profile.**
    
    Can update: full_name, phone, profile_picture_url.
    Email cannot be changed by supervisor (requires admin action).
    """
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Update full name
    if payload.full_name is not None:
        user.full_name = payload.full_name
    
    # Update phone (check uniqueness)
    if payload.phone is not None:
        # Check if phone already taken by another user
        existing = await db.execute(
            select(User).where(
                User.phone == payload.phone,
                User.id != current_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Phone number already registered by another user."
            )
        user.phone = payload.phone
    
    # Update profile picture

    
    await db.commit()
    await db.refresh(user)
    
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
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.post("/change-password")
async def change_supervisor_password(
    payload: SupervisorChangePasswordRequest,
    current_user: SupervisorUser,
    db: DBSession
):
    """
    **Change supervisor password.**
    
    Requirements:
    - Current password must be correct
    - New password: min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char
    - New password and confirm password must match
    
    After successful change, all other sessions are revoked for security.
    """
    from app.models.user import User
    from sqlalchemy import select
    
    # Validate passwords match
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="New passwords do not match."
        )
    
    # Get the user record
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Verify current password
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect."
        )
    
    # Validate new password strength
    errors = []
    if len(payload.new_password) < 8:
        errors.append("Password must be at least 8 characters")
    if not re.search(r'[A-Z]', payload.new_password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', payload.new_password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r'[0-9]', payload.new_password):
        errors.append("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', payload.new_password):
        errors.append("Password must contain at least one special character")
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail="; ".join(errors)
        )
    
    # Hash and update password
    user.password_hash = hash_password(payload.new_password)
    
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
