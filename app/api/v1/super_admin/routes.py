from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Request

from fastapi.responses import Response

from datetime import date, timedelta 

import re
from app.core.security import verify_password, hash_password
from app.repositories.user_repository import UserRepository
from sqlalchemy import select

from app.api.v1.supervisor.routes import SupervisorUser

from app.models.user import User, UserRole

from uuid import uuid4

from datetime import UTC, datetime

from app.dependencies import CurrentUser, require_roles

from app.dependencies import DBSession

from app.models.hostel import HostelStatus

from app.schemas.maintenance import MaintenanceResponse, MaintenanceUpdateRequest

from app.schemas.super_admin import (

    AssignHostelRequest,

    SuperAdminProfileResponse,

    SuperAdminProfileUpdateRequest,

    ValidatePasswordRequest,

    PasswordValidationResponse,

    AssignHostelsRequest,

    ChangePasswordRequest,

    SuperAdminHostelListResponse,

    SuperAdminHostelRejectRequest,

    SuperAdminAdminCreateRequest,

    SuperAdminAdminResponse,

    SuperAdminDashboardResponse,

    SuperAdminHostelCreateRequest,

    SuperAdminHostelResponse,

    SuperAdminSubscriptionResponse,

    SuperAdminSubscriptionCreateRequest,

    SuperAdminSubscriptionUpdateRequest,

    SuperAdminSubscriptionDetailResponse,

)

from app.services.super_admin_service import SuperAdminService

from app.schemas.student import CompleteStudentDetailResponse

from fastapi.exceptions import RequestValidationError

from fastapi.responses import JSONResponse





router = APIRouter()

SuperAdmin = Annotated[CurrentUser, Depends(require_roles("super_admin"))]





def validate_email(email: str) -> bool:

    """

    Validate email format and domain.

    

    Checks:

    - Valid email format (contains @ and .)

    - Domain has at least one dot after @

    - No spaces

    """

    email = email.strip()

    

    # Check for empty

    if not email:

        return False

    

    # Check for spaces

    if ' ' in email:

        return False

    

    # Check for @ symbol

    if '@' not in email:

        return False

    

    # Split into local and domain parts

    local_part, domain_part = email.rsplit('@', 1)

    

    # Check local part is not empty

    if not local_part:

        return False

    

    # Check domain has at least one dot and not empty

    if not domain_part or '.' not in domain_part:

        return False

    

    # Check domain doesn't start or end with dot

    if domain_part.startswith('.') or domain_part.endswith('.'):

        return False

    

    # Check for valid characters (basic check)

    # Allow letters, numbers, dots, hyphens, underscores in local part

    valid_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    return bool(re.match(valid_pattern, email))





@router.get("/dashboard", response_model=SuperAdminDashboardResponse)

async def dashboard(_: SuperAdmin, db: DBSession):

    """**Platform overview** — total hostels, admins, and active subscriptions."""

    return await SuperAdminService(db).get_dashboard()





@router.get("/hostels", response_model=list[SuperAdminHostelResponse])

async def list_hostels(_: SuperAdmin, db: DBSession):

    """**List all hostels** across the platform in all statuses."""

    return await SuperAdminService(db).list_hostels()





@router.get("/hostels/paginated", response_model=SuperAdminHostelListResponse)

async def list_hostels_paginated(

    _: SuperAdmin,

    db: DBSession,

    status: str | None = None,

    page: int = 1,

    per_page: int = 20,

):

    """Spec-compatible paginated hostel list with optional status filter."""

    return await SuperAdminService(db).list_hostels_paginated(status=status, page=page, per_page=per_page)





@router.get("/hostels/{hostel_id}", response_model=SuperAdminHostelResponse)

async def get_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):

    return await SuperAdminService(db).get_hostel(hostel_id)





@router.post("/hostels", response_model=SuperAdminHostelResponse, status_code=201)

async def create_hostel(payload: SuperAdminHostelCreateRequest, _: SuperAdmin, db: DBSession):

    """**Create a new hostel.** Created in `pending_approval` status by default."""

    return await SuperAdminService(db).create_hostel(payload)





@router.post("/hostels/{hostel_id}/images", status_code=201)

async def add_hostel_images(_: SuperAdmin, hostel_id: str, db: DBSession, payload: list[dict]):

    """**Add images to a hostel.** Each item: {url, thumbnail_url?, caption?, is_primary?}"""

    from app.models.hostel import HostelImage

    from sqlalchemy import select

    from app.models.hostel import Hostel

    result = await db.execute(select(Hostel).where(Hostel.id == hostel_id))

    hostel = result.scalar_one_or_none()

    if hostel is None:

        raise HTTPException(status_code=404, detail="Hostel not found.")

    added = []

    for i, img in enumerate(payload[:10]):

        url = img.get("url", "").strip()

        if not url:

            continue

        image = HostelImage(

            hostel_id=hostel_id,

            url=url,

            thumbnail_url=img.get("thumbnail_url", url),

            caption=img.get("caption"),

            image_type=img.get("image_type", "gallery"),

            sort_order=i,

            is_primary=(i == 0 and img.get("is_primary", True)),

        )

        db.add(image)

        added.append({"url": url, "sort_order": i})

    await db.commit()

    return {"hostel_id": hostel_id, "images_added": len(added)}





@router.patch("/hostels/{hostel_id}/approve", response_model=SuperAdminHostelResponse)

async def approve_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):

    """**Approve a hostel** — sets status to `active`, making it publicly visible."""

    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.ACTIVE)





@router.patch("/hostels/{hostel_id}/reject", response_model=SuperAdminHostelResponse)

async def reject_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):

    """**Reject a hostel** — sets status to `rejected`. Hostel will not appear publicly."""

    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.REJECTED)





@router.post("/hostels/{hostel_id}/approve", response_model=SuperAdminHostelResponse)

async def approve_hostel_post(hostel_id: str, _: SuperAdmin, db: DBSession):

    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.ACTIVE)





@router.post("/hostels/{hostel_id}/reject", response_model=SuperAdminHostelResponse)

async def reject_hostel_post(hostel_id: str, payload: SuperAdminHostelRejectRequest, _: SuperAdmin, db: DBSession):

    _ = payload.reason  # reason accepted for contract; model currently has no rejection_reason field.

    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.REJECTED)





@router.post("/hostels/{hostel_id}/suspend", response_model=SuperAdminHostelResponse)

async def suspend_hostel_post(hostel_id: str, _: SuperAdmin, db: DBSession):

    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.SUSPENDED)





@router.patch("/hostels/{hostel_id}/suspend", response_model=SuperAdminHostelResponse)

async def suspend_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):

    """**Suspend a hostel** — temporarily removes it from public listing."""

    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.SUSPENDED)





@router.get("/admins", response_model=list[SuperAdminAdminResponse])

async def list_admins(_: SuperAdmin, db: DBSession):

    """**List all hostel admins** on the platform."""

    return await SuperAdminService(db).list_admins()



@router.post("/admins", response_model=SuperAdminAdminResponse, status_code=201)

async def create_admin(payload: SuperAdminAdminCreateRequest, _: SuperAdmin, db: DBSession):

    """

    **Create a new hostel admin account.**

    

    The created user gets role `hostel_admin`. Use `assign-hostels` next

    to give them access to specific hostels.

    

    Requirements:

    - Email must be valid format (e.g., user@example.com)

    - Phone must be 10 digits (Indian format)

    - Password must be at least 8 chars with uppercase, lowercase, and number

    - Full name must be at least 2 characters

    """

    from app.core.security import hash_password

    import re

    

    # Normalize email (lowercase)

    normalized_email = payload.email.lower().strip()

    

    # CHECK FOR EXISTING EMAIL - This is the critical part

    existing_email = await db.execute(

        select(User).where(User.email == normalized_email)

    )

    if existing_email.scalar_one_or_none():

        raise HTTPException(

            status_code=status.HTTP_409_CONFLICT,

            detail=f"Email '{payload.email}' is already registered."

        )

    

    # Normalize phone and check for existing phone

    normalized_phone = re.sub(r'[^0-9]', '', payload.phone)

    

    # Handle Indian number format (10 digits after removing +91 or 0)

    if normalized_phone.startswith('91') and len(normalized_phone) == 12:

        normalized_phone = normalized_phone[2:]

    elif normalized_phone.startswith('0'):

        normalized_phone = normalized_phone[1:]

    

    if len(normalized_phone) == 10 and not normalized_phone[0] in ['6', '7', '8', '9']:

        raise HTTPException(

            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

            detail="Indian phone number must start with 6, 7, 8, or 9"

        )

    

    # CHECK FOR EXISTING PHONE

    existing_phone = await db.execute(

        select(User).where(User.phone == normalized_phone)

    )

    if existing_phone.scalar_one_or_none():

        raise HTTPException(

            status_code=status.HTTP_409_CONFLICT,

            detail=f"Phone number '{payload.phone}' is already registered."

        )

    

    # Validate password strength

    if len(payload.password) < 8:

        raise HTTPException(

            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

            detail="Password must be at least 8 characters"

        )

    if not re.search(r'[A-Z]', payload.password):

        raise HTTPException(

            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

            detail="Password must contain at least one uppercase letter"

        )

    if not re.search(r'[a-z]', payload.password):

        raise HTTPException(

            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

            detail="Password must contain at least one lowercase letter"

        )

    if not re.search(r'[0-9]', payload.password):

        raise HTTPException(

            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

            detail="Password must contain at least one number"

        )

    

    # Create admin user with normalized phone

    admin = User(

        email=normalized_email,

        phone=normalized_phone,

        full_name=payload.full_name.strip(),

        password_hash=hash_password(payload.password),

        role=UserRole.HOSTEL_ADMIN,

        is_active=True,

        is_email_verified=True,

        is_phone_verified=True,

    )

    

    db.add(admin)

    await db.commit()

    await db.refresh(admin)

    

    return admin



@router.post("/admins/{admin_id}/assign-hostels")

async def assign_hostels(

    admin_id: str, 

    payload: AssignHostelsRequest, 

    current_user: SuperAdmin, 

    db: DBSession

):

    """

    **Assign hostels to an admin.**



    Replaces existing assignments. Pass an array of `hostel_ids`.

    The admin will only be able to manage the assigned hostels.

    """

    from app.models.hostel import AdminHostelMapping, Hostel

    from sqlalchemy import select, delete

    

    # Verify admin exists

    result = await db.execute(

        select(User).where(User.id == admin_id, User.role == UserRole.HOSTEL_ADMIN)

    )

    admin_user = result.scalar_one_or_none()

    

    if admin_user is None:

        raise HTTPException(status_code=404, detail="Admin not found.")

    

    # Delete existing assignments

    await db.execute(

        delete(AdminHostelMapping).where(AdminHostelMapping.admin_id == admin_id)

    )

    

    # Create new assignments

    for index, hostel_id in enumerate(payload.hostel_ids):

        # Verify hostel exists

        hostel_result = await db.execute(select(Hostel).where(Hostel.id == hostel_id))

        if hostel_result.scalar_one_or_none() is None:

            raise HTTPException(status_code=404, detail=f"Hostel {hostel_id} not found.")

        

        mapping = AdminHostelMapping(

            id=uuid4(),

            admin_id=admin_id,

            hostel_id=hostel_id,

            is_primary=(index == 0),

            assigned_by=current_user.id,

            assigned_at=datetime.now(UTC)

        )

        db.add(mapping)

    

    await db.commit()

    return {"admin_id": admin_id, "hostel_ids": payload.hostel_ids}



@router.post("/admins/{admin_id}/assign-hostel")

async def assign_hostel(admin_id: str, payload: AssignHostelRequest, current_user: SuperAdmin, db: DBSession):

    return await SuperAdminService(db).assign_hostel(

        actor_id=current_user.id,

        admin_id=admin_id,

        payload=payload,

    )





# ==================== SUBSCRIPTION ENDPOINTS ====================





@router.get("/subscriptions/stats")
async def get_subscription_stats(
    _: SuperAdmin,
    db: DBSession,
):
    """
    Get subscription statistics for dashboard.
    """
    from sqlalchemy import text
    
    try:
        # Get total subscriptions
        result = await db.execute(text("SELECT COUNT(*) FROM subscriptions"))
        total = result.scalar() or 0
        
        # Get active subscriptions
        result = await db.execute(text("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"))
        active = result.scalar() or 0
        
        # Get expired
        result = await db.execute(text("SELECT COUNT(*) FROM subscriptions WHERE status = 'expired'"))
        expired = result.scalar() or 0
        
        # Get cancelled
        result = await db.execute(text("SELECT COUNT(*) FROM subscriptions WHERE status = 'cancelled'"))
        cancelled = result.scalar() or 0
        
        # Get revenue
        result = await db.execute(text("SELECT COALESCE(SUM(price_monthly), 0) FROM subscriptions WHERE status = 'active'"))
        revenue = float(result.scalar() or 0)
        
        # Get tier distribution
        result = await db.execute(text("SELECT tier, COUNT(*) FROM subscriptions WHERE status = 'active' GROUP BY tier"))
        tier_dist = {}
        for row in result:
            tier_dist[row[0]] = row[1]
        
        return {
            "total_subscriptions": total,
            "active_subscriptions": active,
            "expired_subscriptions": expired,
            "cancelled_subscriptions": cancelled,
            "expiring_soon": 0,
            "monthly_recurring_revenue": revenue,
            "tier_distribution": tier_dist,
        }
    except Exception as e:
        return {
            "total_subscriptions": 0,
            "active_subscriptions": 0,
            "expired_subscriptions": 0,
            "cancelled_subscriptions": 0,
            "expiring_soon": 0,
            "monthly_recurring_revenue": 0.0,
            "tier_distribution": {},
        }


@router.get("/subscriptions", response_model=list[SuperAdminSubscriptionDetailResponse])
async def list_subscriptions(
    _: SuperAdmin,
    db: DBSession,
    status_filter: str | None = Query(None, description="Filter by status: active, expired, cancelled"),
    hostel_id: str | None = Query(None, description="Filter by hostel ID"),
):
    """List all hostel subscriptions with optional filtering."""
    from sqlalchemy import select
    from app.models.operations import Subscription
    from app.models.hostel import Hostel
    
    query = select(Subscription)
    
    if status_filter:
        query = query.where(Subscription.status == status_filter)
    
    if hostel_id:
        query = query.where(Subscription.hostel_id == hostel_id)
    
    query = query.order_by(Subscription.created_at.desc())
    
    result = await db.execute(query)
    subscriptions = list(result.scalars().all())
    
    # Build response manually
    response = []
    for sub in subscriptions:
        # Get hostel name
        hostel_result = await db.execute(
            select(Hostel.name).where(Hostel.id == sub.hostel_id)
        )
        hostel_name = hostel_result.scalar_one_or_none()
        
        response.append({
            "id": str(sub.id),
            "hostel_id": str(sub.hostel_id),
            "hostel_name": hostel_name,
            "tier": sub.tier,
            "price_monthly": float(sub.price_monthly),
            "start_date": sub.start_date.isoformat(),
            "end_date": sub.end_date.isoformat(),
            "status": sub.status,
            "auto_renew": sub.auto_renew,
            "created_at": sub.created_at,
            "updated_at": sub.updated_at,
        })
    
    return response

@router.get("/subscriptions/{subscription_id}", response_model=SuperAdminSubscriptionDetailResponse)
async def get_subscription(
    subscription_id: str,
    _: SuperAdmin,
    db: DBSession,
):
    """Get a single subscription by ID."""
    from sqlalchemy import select
    from app.models.operations import Subscription
    from app.models.hostel import Hostel
    from datetime import date
    
    try:
        # Validate UUID format
        import uuid
        try:
            uuid.UUID(subscription_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invalid subscription ID format"
            )
        
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with id '{subscription_id}' not found."
            )
        
        hostel_result = await db.execute(
            select(Hostel).where(Hostel.id == subscription.hostel_id)
        )
        hostel = hostel_result.scalar_one_or_none()
        
        days_remaining = None
        if subscription.status == "active" and subscription.end_date:
            days_remaining = (subscription.end_date - date.today()).days
            days_remaining = max(0, days_remaining)
        
        return {
            "id": str(subscription.id),
            "hostel_id": str(subscription.hostel_id),
            "hostel_name": hostel.name if hostel else None,
            "tier": subscription.tier,
            "price_monthly": float(subscription.price_monthly),
            "start_date": subscription.start_date.isoformat(),
            "end_date": subscription.end_date.isoformat(),
            "status": subscription.status,
            "auto_renew": subscription.auto_renew,
            "days_remaining": days_remaining,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found"
        )
@router.post("/subscriptions", status_code=201)
async def create_subscription(
    request: Request,
    _: SuperAdmin,
    db: DBSession,
):
    """Create a new subscription for a hostel."""
    from sqlalchemy import select
    from app.models.operations import Subscription
    from app.models.hostel import Hostel
    from datetime import date
    
    # Parse body manually to avoid validation issues
    body = await request.json()
    
    hostel_id = body.get("hostel_id")
    tier = body.get("tier")
    price_monthly = body.get("price_monthly")
    start_date = body.get("start_date")
    end_date = body.get("end_date")
    auto_renew = body.get("auto_renew", True)
    status = body.get("status", "active")
    
    # Validate required fields
    if not hostel_id:
        raise HTTPException(status_code=400, detail="hostel_id is required")
    if not tier:
        raise HTTPException(status_code=400, detail="tier is required")
    if price_monthly is None:
        raise HTTPException(status_code=400, detail="price_monthly is required")
    
    # Parse dates
    try:
        start_date = date.fromisoformat(start_date) if start_date else date.today()
        end_date = date.fromisoformat(end_date) if end_date else date.today()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Check if hostel exists
    hostel_result = await db.execute(
        select(Hostel).where(Hostel.id == hostel_id)
    )
    hostel = hostel_result.scalar_one_or_none()
    if not hostel:
        raise HTTPException(
            status_code=404,
            detail=f"Hostel with id '{hostel_id}' not found."
        )
    
    # Check for existing active subscription
    existing = await db.execute(
        select(Subscription).where(
            Subscription.hostel_id == hostel_id,
            Subscription.status == "active"
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Hostel already has an active subscription. Please cancel it first."
        )
    
    # Create subscription
    subscription = Subscription(
        hostel_id=hostel_id,
        tier=tier,
        price_monthly=float(price_monthly),
        start_date=start_date,
        end_date=end_date,
        status=status,
        auto_renew=auto_renew,
    )
    
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "id": str(subscription.id),
        "hostel_id": str(subscription.hostel_id),
        "hostel_name": hostel.name,
        "tier": subscription.tier,
        "price_monthly": float(subscription.price_monthly),
        "start_date": subscription.start_date.isoformat(),
        "end_date": subscription.end_date.isoformat(),
        "status": subscription.status,
        "auto_renew": subscription.auto_renew,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
    }

@router.patch("/subscriptions/{subscription_id}", response_model=SuperAdminSubscriptionDetailResponse)
async def update_subscription(
    subscription_id: str,
    payload: SuperAdminSubscriptionUpdateRequest,
    _: SuperAdmin,
    db: DBSession,
):
    """Update an existing subscription."""
    from app.models.hostel import Hostel
    from app.models.operations import Subscription
    from datetime import date
    
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with id '{subscription_id}' not found."
        )
    
    update_data = payload.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if value is not None:
            setattr(subscription, field, value)
    
    await db.commit()
    await db.refresh(subscription)
    
    hostel_result = await db.execute(
        select(Hostel).where(Hostel.id == subscription.hostel_id)
    )
    hostel = hostel_result.scalar_one_or_none()
    
    days_remaining = None
    if subscription.status == "active" and subscription.end_date:
        days_remaining = (subscription.end_date - date.today()).days
        days_remaining = max(0, days_remaining)
    
    return {
        "id": str(subscription.id),
        "hostel_id": str(subscription.hostel_id),
        "hostel_name": hostel.name if hostel else None,
        "tier": subscription.tier,
        "price_monthly": float(subscription.price_monthly),
        "start_date": subscription.start_date.isoformat(),
        "end_date": subscription.end_date.isoformat(),
        "status": subscription.status,
        "auto_renew": subscription.auto_renew,
        "days_remaining": days_remaining,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
    }

@router.post("/subscriptions/{subscription_id}/cancel", response_model=dict)
async def cancel_subscription(
    subscription_id: str,
    _: SuperAdmin,
    db: DBSession,
):
    """Cancel an active subscription."""
    from sqlalchemy import select
    from app.models.operations import Subscription
    
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found"
        )
    
    if subscription.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel subscription with status '{subscription.status}'"
        )
    
    subscription.status = "cancelled"
    subscription.auto_renew = False
    
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "id": str(subscription.id),
        "status": subscription.status,
        "auto_renew": subscription.auto_renew,
        "message": "Subscription cancelled successfully"
    }

@router.delete("/subscriptions/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: str,
    _: SuperAdmin,
    db: DBSession,
):
    """Delete a subscription (hard delete)."""
    from sqlalchemy import select
    from app.models.operations import Subscription
    
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found"
        )
    
    if subscription.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active subscription. Cancel it first."
        )
    
    await db.delete(subscription)
    await db.commit()
    
    return Response(status_code=204)

@router.get("/profile", response_model=SuperAdminProfileResponse)
async def get_super_admin_profile(
    current_user: SuperAdmin,
    db: DBSession,
):
    """
    **Get super admin profile information.**
    
    Returns personal details including name, email, phone.
    """
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "profile_picture_url": user.profile_picture_url,
        "is_email_verified": user.is_email_verified,
        "is_phone_verified": user.is_phone_verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

@router.patch("/profile", response_model=SuperAdminProfileResponse)
async def update_super_admin_profile(
    payload: SuperAdminProfileUpdateRequest,
    current_user: SuperAdmin,
    db: DBSession,
):
    """
    **Update super admin profile.**
    
    Can update: full_name, phone, profile_picture_url.
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
        # Validate phone format
        import re
        digits_only = re.sub(r'[^0-9]', '', payload.phone)
        
        if len(digits_only) < 10 or len(digits_only) > 13:
            raise HTTPException(
                status_code=400,
                detail="Phone number must have between 10 and 13 digits."
            )
        
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
    if payload.profile_picture_url is not None:
        user.profile_picture_url = payload.profile_picture_url
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "profile_picture_url": user.profile_picture_url,
        "is_email_verified": user.is_email_verified,
        "is_phone_verified": user.is_phone_verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.post("/change-password")
async def change_super_admin_password(
    payload: ChangePasswordRequest,
    current_user: SuperAdmin,
    db: DBSession
):
    """
    **Change super admin password.**
    
    Requirements:
    - Current password must be correct
    - New password: min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char
    - New password and confirm password must match
    
    After successful change, all other sessions are revoked for security.
    """
    from app.models.user import User
    from sqlalchemy import select
    from datetime import UTC, datetime
    
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
    
    # Revoke all other sessions for security
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

@router.post("/validate-password", response_model=PasswordValidationResponse)
async def validate_password(payload: ValidatePasswordRequest):
    """
    Validate password strength without changing it.
    Returns 200 even for invalid passwords (with errors list).
    """
    errors = []
    
    if len(payload.password) < 8:
        errors.append("Password must be at least 8 characters")
    if not re.search(r'[A-Z]', payload.password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', payload.password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r'[0-9]', payload.password):
        errors.append("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', payload.password):
        errors.append("Password must contain at least one special character")
    
    # Always return 200, even for invalid passwords
    return PasswordValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors
    )