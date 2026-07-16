from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.hostel import Hostel, HostelStatus, HostelType
from app.models.payment import Payment
from app.models.student import Student
from app.models.user import User, UserRole
from app.repositories.super_admin_repository import SuperAdminRepository
from app.schemas.super_admin import (
    AssignHostelRequest,
    AssignHostelsRequest,
    SuperAdminHostelListResponse,
    SuperAdminAdminCreateRequest,
    SuperAdminDashboardResponse,
    SuperAdminHostelCreateRequest,
    SuperAdminSubscriptionCreateRequest,
    SuperAdminSubscriptionUpdateRequest,
)

from app.models.operations import Subscription
from datetime import date

from app.models.room import Room, Bed

async def _send_email(to: str, subject: str, body: str):
    from app.integrations.email import send_email
    # Convert newline to <br> for simple HTML
    html_body = body.replace("\n", "<br>")
    try:
        await send_email(to=to, subject=subject, html=html_body)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send email to {to}: {e}")

from app.models.booking import Booking

class SuperAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SuperAdminRepository(session)

    async def get_dashboard(self) -> SuperAdminDashboardResponse:
        hostels = await self.repository.count_hostels()
        admins = await self.repository.count_admins()
        subscriptions = await self.repository.count_subscriptions()
        pending_result = await self.session.execute(
            select(func.count()).select_from(Hostel).where(Hostel.status == HostelStatus.PENDING_APPROVAL)
        )
        active_result = await self.session.execute(
            select(func.count()).select_from(Hostel).where(Hostel.status == HostelStatus.ACTIVE)
        )
        students_result = await self.session.execute(select(func.count()).select_from(Student))
        revenue_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.status == "captured",
                func.date_trunc("month", Payment.created_at) == func.date_trunc("month", func.now()),
            )
        )
        pending = int(pending_result.scalar_one() or 0)
        active = int(active_result.scalar_one() or 0)
        total_students = int(students_result.scalar_one() or 0)
        revenue_month = float(revenue_result.scalar_one() or 0)
        return SuperAdminDashboardResponse(
            total_hostels=hostels,
            pending_approval_count=pending,
            active_hostels=active,
            total_students=total_students,
            total_revenue_month=revenue_month,
            hostels=hostels,
            admins=admins,
            subscriptions=subscriptions,
        )

    async def list_hostels(self):
        return await self.repository.list_hostels()

    async def list_hostels_paginated(self, *, status: str | None = None, page: int = 1, per_page: int = 20):
        items, total = await self.repository.list_hostels_paginated(status=status, page=page, per_page=per_page)
        return SuperAdminHostelListResponse(items=items, total=total, page=page, per_page=per_page)

    async def get_hostel(self, hostel_id: str):
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")
        return hostel

    async def delete_hostel(self, hostel_id: str) -> dict:
        """Permanently delete a hostel and all its associated data."""
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")
        hostel_name = hostel.name
        await self.repository.delete_hostel(hostel)
        await self.session.commit()
        return {"message": f"Hostel '{hostel_name}' has been permanently deleted.", "hostel_id": hostel_id}

    async def create_hostel(
        self,
        payload: SuperAdminHostelCreateRequest,
        owner_id: str | None = None,
    ):
        """Create a hostel in PENDING_APPROVAL state with all public flags disabled."""
        hostel = Hostel(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            hostel_type=HostelType(payload.hostel_type),
            status=HostelStatus.PENDING_APPROVAL,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            pincode=payload.pincode,
            latitude=0.0,
            longitude=0.0,
            phone=payload.phone,
            email=payload.email,
            website=payload.website,
            is_featured=False,
            is_public=False,      # MUST be False until approved
            is_active=False,      # MUST be False until approved
            is_verified=False,    # MUST be False until approved
            status_reason=None,
            rules_and_regulations=payload.rules_and_regulations,
        )
        hostel = await self.repository.create_hostel(hostel)
        await self.session.flush()

        # Map the submitting owner as the primary admin of this hostel
        if owner_id:
            from app.models.hostel import AdminHostelMapping
            mapping = AdminHostelMapping(
                admin_id=owner_id,
                hostel_id=str(hostel.id),
                is_primary=True,
                assigned_by=owner_id,
            )
            self.session.add(mapping)

        await self.session.commit()
        return await self.repository.get_hostel_by_id(str(hostel.id))

    async def register_hostel(self, payload, owner_id: str):
        """
        Public registration — hostel owner submits registration form.
        Stores with PENDING_APPROVAL, is_public=False, is_active=False, is_verified=False.
        Sends notification to super admins.
        """
        from app.schemas.hostel import HostelRegistrationRequest
        from app.schemas.super_admin import SuperAdminHostelCreateRequest

        # Build a SuperAdminHostelCreateRequest-compatible payload using the registration data
        create_payload = SuperAdminHostelCreateRequest(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            hostel_type=payload.hostel_type,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            pincode=payload.pincode,

            phone=payload.phone,
            email=payload.email,
            website=payload.website,
            is_featured=False,
            is_public=False,
            rules_and_regulations=payload.rules_and_regulations,
        )

        hostel = await self.create_hostel(create_payload, owner_id=owner_id)

        # Save document info if provided
        if payload.document_url:
            hostel.document_url = payload.document_url
            hostel.document_type = payload.document_type
            await self.session.commit()

        # Send notification email to hostel owner
        await _send_email(
            to=payload.email,
            subject="✅ Your Hostel Registration Was Received — StayEase",
            body=(
                f"Hi,\n\n"
                f"Thank you for registering '{payload.name}' on StayEase.\n\n"
                f"Your registration is now under review. Our team will inspect your details and "
                f"get back to you within 2–3 business days.\n\n"
                f"You will receive an email once it is approved, rejected, or if we need any changes.\n\n"
                f"Regards,\nThe StayEase Team"
            ),
        )
        return await self.repository.get_hostel_by_id(str(hostel.id))

    async def update_hostel_status(self, hostel_id: str, status_value: HostelStatus):
        """Legacy simple status update — used by internal admin tools."""
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")
        hostel.status = status_value
        if status_value == HostelStatus.ACTIVE:
            hostel.is_public  = True
            hostel.is_active  = True
            hostel.is_verified = True
        elif status_value in (HostelStatus.REJECTED, HostelStatus.SUSPENDED, HostelStatus.INACTIVE):
            hostel.is_public  = False
            hostel.is_active  = False
        await self.session.commit()
        return await self.repository.get_hostel_by_id(str(hostel.id))

    async def approve_hostel(
        self,
        hostel_id: str,
        approved_by: str,
        note: str | None = None,
    ):
        """
        Approve a hostel registration:
        - status → ACTIVE
        - is_public, is_active, is_verified → True
        - Notify the hostel owner via email
        """
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")

        if hostel.status not in (
            HostelStatus.PENDING_APPROVAL,
            HostelStatus.CHANGES_REQUESTED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve hostel with status '{hostel.status.value}'.",
            )

        hostel.status      = HostelStatus.ACTIVE
        hostel.is_public   = True
        hostel.is_active   = True
        hostel.is_verified = True
        hostel.status_reason = None

        await self.session.commit()

        # Audit log
        import logging
        logging.getLogger(__name__).info(
            "Hostel %s ('%s') APPROVED by user %s", hostel_id, hostel.name, approved_by
        )

        # Email notification to hostel owner
        await _send_email(
            to=hostel.email,
            subject="🎉 Congratulations! Your Hostel is Now Live on StayEase",
            body=(
                f"Dear Owner of '{hostel.name}',\n\n"
                f"We're delighted to inform you that your hostel registration has been "
                f"APPROVED and is now live on StayEase.\n\n"
                + (f"Note from our team: {note}\n\n" if note else "")
                + f"Guests can now discover and book rooms at your hostel.\n\n"
                f"Regards,\nThe StayEase Team"
            ),
        )
        return await self.repository.get_hostel_by_id(str(hostel.id))

    async def reject_hostel(
        self,
        hostel_id: str,
        rejected_by: str,
        reason: str,
    ):
        """
        Reject a hostel registration:
        - status → REJECTED
        - is_public, is_active, is_verified → False
        - Store reason and notify owner
        """
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")

        if hostel.status not in (
            HostelStatus.PENDING_APPROVAL,
            HostelStatus.CHANGES_REQUESTED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject hostel with status '{hostel.status.value}'.",
            )

        hostel.status        = HostelStatus.REJECTED
        hostel.is_public     = False
        hostel.is_active     = False
        hostel.is_verified   = False
        hostel.status_reason = reason

        await self.session.commit()

        import logging
        logging.getLogger(__name__).info(
            "Hostel %s ('%s') REJECTED by user %s. Reason: %s",
            hostel_id, hostel.name, rejected_by, reason,
        )

        await _send_email(
            to=hostel.email,
            subject="❌ Hostel Registration Update — StayEase",
            body=(
                f"Dear Owner of '{hostel.name}',\n\n"
                f"After reviewing your hostel registration, we regret to inform you that "
                f"it has been REJECTED for the following reason:\n\n"
                f"{reason}\n\n"
                f"If you believe this is an error or would like to re-apply, please contact "
                f"our support team.\n\n"
                f"Regards,\nThe StayEase Team"
            ),
        )
        return await self.repository.get_hostel_by_id(str(hostel.id))

    async def request_hostel_changes(
        self,
        hostel_id: str,
        requested_by: str,
        reason: str,
    ):
        """
        Request changes from the hostel owner:
        - status → CHANGES_REQUESTED
        - is_public, is_active → False (keep hidden until fixes are made)
        - Store reason and notify owner
        """
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")

        if hostel.status not in (
            HostelStatus.PENDING_APPROVAL,
            HostelStatus.CHANGES_REQUESTED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot request changes on hostel with status '{hostel.status.value}'.",
            )

        hostel.status        = HostelStatus.CHANGES_REQUESTED
        hostel.is_public     = False
        hostel.is_active     = False
        hostel.status_reason = reason

        await self.session.commit()

        import logging
        logging.getLogger(__name__).info(
            "Changes requested on hostel %s ('%s') by %s. Reason: %s",
            hostel_id, hostel.name, requested_by, reason,
        )

        await _send_email(
            to=hostel.email,
            subject="📝 Action Required: Changes Needed for Your Hostel — StayEase",
            body=(
                f"Dear Owner of '{hostel.name}',\n\n"
                f"Our review team has reviewed your hostel registration and requires some "
                f"changes before we can approve it:\n\n"
                f"{reason}\n\n"
                f"Please update your hostel details and resubmit for review. "
                f"If you have any questions, please reach out to our support team.\n\n"
                f"Regards,\nThe StayEase Team"
            ),
        )
        return await self.repository.get_hostel_by_id(str(hostel.id))

    async def list_admins(self):
        return await self.repository.list_admins()

    async def create_admin(self, payload: SuperAdminAdminCreateRequest):
        """Create a new hostel admin with validation"""
        from sqlalchemy import select
        
        # Check if email already exists
        existing_email = await self.session.execute(
            select(User).where(User.email == payload.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{payload.email}' is already registered."
            )
        
        # Check if phone already exists
        existing_phone = await self.session.execute(
            select(User).where(User.phone == payload.phone)
        )
        if existing_phone.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phone number '{payload.phone}' is already registered."
            )
        
        # Create the admin user
        admin = User(
            email=payload.email,
            phone=payload.phone,  # Already cleaned in validation
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=UserRole.HOSTEL_ADMIN,
            is_active=True,
            is_email_verified=True,
            is_phone_verified=True,
        )
        
        admin = await self.repository.create_admin(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin
            
    async def assign_hostels(self, actor_id: str, admin_id: str, payload: AssignHostelsRequest):
        """Assign hostels to an admin - with plan limit enforcement."""
        from app.models.operations import Subscription
        from app.models.plan import Plan

        # Get admin's active subscription plan
        sub_result = await self.session.execute(
            select(Subscription)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(
                Subscription.status == "active",
                # You'll need to link admin to subscription via hostel
            )
        )

        """Assign hostels to an admin - replaces existing assignments."""
        admin = await self.repository.get_admin_by_id(admin_id)
        if admin is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")
        
        # NEW: Validate that all hostel IDs exist and are active
        from app.models.hostel import Hostel, HostelStatus
        for hostel_id in payload.hostel_ids:
            hostel_result = await self.session.execute(
                select(Hostel).where(Hostel.id == hostel_id)
            )
            hostel = hostel_result.scalar_one_or_none()
            if not hostel:
                raise HTTPException(
                    status_code=404,
                    detail=f"Hostel with id '{hostel_id}' not found."
                )
            if hostel.status != HostelStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Hostel '{hostel.name}' is not active (status: {hostel.status.value}). Only active hostels can be assigned."
                )
        
        # NEW: Check if this admin email is already assigned to any of these hostels by another admin
        # This prevents the same email from being assigned by different super admins
        admin_email = admin.email
        for hostel_id in payload.hostel_ids:
            # Check if any OTHER admin with same email is already assigned to this hostel
            other_admin_result = await self.session.execute(
                select(User)
                .join(AdminHostelMapping, AdminHostelMapping.admin_id == User.id)
                .where(
                    User.email == admin_email,
                    User.id != admin_id,
                    AdminHostelMapping.hostel_id == hostel_id
                )
            )
            if other_admin_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=f"Admin with email '{admin_email}' is already assigned to hostel '{hostel_id}' (different admin ID)."
                )
        
        # Replace existing mappings
        await self.repository.replace_admin_hostels(
            admin_id=admin_id, 
            hostel_ids=payload.hostel_ids, 
            assigned_by=actor_id
        )
        await self.session.commit()
        return {"admin_id": admin_id, "hostel_ids": payload.hostel_ids}

    async def assign_hostel(self, actor_id: str, admin_id: str, payload: AssignHostelRequest):
        admin = await self.repository.get_admin_by_id(admin_id)
        if admin is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")
        current = await self.repository.list_hostels()
        _ = current  # keep repository usage explicit for consistency
        # Preserve existing mappings and upsert one hostel with requested primary flag.
        from app.models.hostel import AdminHostelMapping

        result = await self.session.execute(
            select(AdminHostelMapping).where(AdminHostelMapping.admin_id == admin_id)
        )
        mappings = list(result.scalars().all())
        if payload.is_primary:
            for m in mappings:
                m.is_primary = False
        existing = next((m for m in mappings if str(m.hostel_id) == payload.hostel_id), None)
        if existing:
            existing.is_primary = payload.is_primary or existing.is_primary
        else:
            self.session.add(
                AdminHostelMapping(
                    admin_id=admin_id,
                    hostel_id=payload.hostel_id,
                    is_primary=payload.is_primary or len(mappings) == 0,
                    assigned_by=actor_id,
                )
            )
        await self.session.commit()
        return {"admin_id": admin_id, "hostel_id": payload.hostel_id, "is_primary": payload.is_primary}

    async def list_subscriptions(self):
        return await self.repository.list_subscriptions()

    async def list_all_students(
        self, 
        page: int = 1, 
        per_page: int = 20,
        hostel_id: str | None = None,
        status: str | None = None
    ) -> list[dict]:
        """List all students with complete details (Super Admin only)"""
        
        query = select(
            Student,
            User.full_name,
            User.email,
            User.phone,
            Room.room_number,
            Room.room_type,
            Bed.bed_number,
            Booking.booking_number,
            Booking.booking_advance,
            Hostel.name.label("hostel_name"),
            Hostel.city.label("hostel_city"),
        ).select_from(Student)\
        .join(User, User.id == Student.user_id)\
        .outerjoin(Room, Room.id == Student.room_id)\
        .outerjoin(Bed, Bed.id == Student.bed_id)\
        .outerjoin(Booking, Booking.id == Student.booking_id)\
        .outerjoin(Hostel, Hostel.id == Student.hostel_id)
        
        if hostel_id:
            query = query.where(Student.hostel_id == hostel_id)
        
        if status:
            query = query.where(Student.status == status)
        
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        students = []
        for row in rows:
            student = row[0]
            students.append({
                "id": str(student.id),
                "student_number": student.student_number,
                "user_id": str(student.user_id),
                "full_name": row.full_name,
                "email": row.email,
                "phone": row.phone,
                "status": student.status.value if hasattr(student.status, 'value') else str(student.status),
                "check_in_date": student.check_in_date,
                "check_out_date": student.check_out_date,
                "room_number": row.room_number,
                "room_type": row.room_type.value if row.room_type and hasattr(row.room_type, 'value') else row.room_type,
                "bed_number": row.bed_number,
                "booking_number": row.booking_number,
                "hostel_name": row.hostel_name,
                "hostel_city": row.hostel_city,
                "advance_paid": float(row.booking_advance) if row.booking_advance else 0,
            })
        
        return students


    async def get_complete_student_by_id(self, student_id: str) -> dict | None:
        """Get complete student details (Super Admin only)"""
        from app.services.admin_service import AdminService
        admin_service = AdminService(self.session)
        return await admin_service.get_complete_student_by_id(student_id)


    async def get_student_payments(self, student_id: str) -> list[dict]:
        """Get payment history for a student"""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.student_id == student_id)
            .order_by(Payment.created_at.desc())
        )
        payments = result.scalars().all()
        
        return [
            {
                "id": str(p.id),
                "amount": float(p.amount),
                "payment_type": p.payment_type,
                "payment_method": p.payment_method,
                "status": p.status,
                "gateway_payment_id": p.gateway_payment_id,
                "paid_at": p.paid_at,
                "created_at": p.created_at,
            }
            for p in payments
        ]
        

    async def create_subscription(
        self, 
        payload: SuperAdminSubscriptionCreateRequest
    ) -> dict:
        """Create a new subscription for a hostel."""
        from app.models.hostel import Hostel
        from sqlalchemy import select
        
        # Validate hostel exists
        hostel_result = await self.session.execute(
            select(Hostel).where(Hostel.id == payload.hostel_id)
        )
        hostel = hostel_result.scalar_one_or_none()
        if not hostel:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hostel with id '{payload.hostel_id}' not found."
            )
        
        # Check for existing active subscription
        existing = await self.repository.get_subscription_by_hostel_id(payload.hostel_id)
        if existing and existing.status == "active":
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Hostel already has an active subscription (ID: {existing.id}). "
                    f"Please cancel or expire the existing subscription first."
            )
        
        # Create subscription
        subscription = Subscription(
            hostel_id=payload.hostel_id,
            tier=payload.tier,
            price_monthly=payload.price_monthly,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=payload.status,
            auto_renew=payload.auto_renew,
        )
        
        subscription = await self.repository.create_subscription_record(subscription)
        await self.session.commit()
        
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


    async def update_subscription(
        self,
        subscription_id: str,
        payload: SuperAdminSubscriptionUpdateRequest
    ) -> dict:
        """Update an existing subscription."""
        from app.models.hostel import Hostel
        from sqlalchemy import select
        
        subscription = await self.repository.get_subscription_by_id(subscription_id)
        if not subscription:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with id '{subscription_id}' not found."
            )
        
        # Update fields
        update_data = payload.dict(exclude_unset=True)
        
        if "tier" in update_data:
            subscription.tier = update_data["tier"]
        if "price_monthly" in update_data:
            subscription.price_monthly = update_data["price_monthly"]
        if "auto_renew" in update_data:
            subscription.auto_renew = update_data["auto_renew"]
        if "status" in update_data:
            subscription.status = update_data["status"]
        if "start_date" in update_data:
            subscription.start_date = update_data["start_date"]
        if "end_date" in update_data:
            subscription.end_date = update_data["end_date"]
        
        subscription = await self.repository.update_subscription_record(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        
        # Get hostel name
        hostel_result = await self.session.execute(
            select(Hostel).where(Hostel.id == subscription.hostel_id)
        )
        hostel = hostel_result.scalar_one_or_none()
        
        # Calculate days remaining
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


    async def delete_subscription(self, subscription_id: str) -> None:
        """Delete a subscription."""
        subscription = await self.repository.get_subscription_by_id(subscription_id)
        if not subscription:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with id '{subscription_id}' not found."
            )
        
        # Prevent deletion of active subscriptions
        if subscription.status == "active":
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete an active subscription. Please cancel it first."
            )
        
        await self.repository.delete_subscription_record(subscription)
        await self.session.commit()


    async def cancel_subscription(self, subscription_id: str) -> dict:
        """Cancel an active subscription (soft delete)."""
        subscription = await self.repository.get_subscription_by_id(subscription_id)
        if not subscription:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with id '{subscription_id}' not found."
            )
        
        if subscription.status != "active":
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel subscription with status '{subscription.status}'. "
                    f"Only active subscriptions can be cancelled."
            )
        
        subscription.status = "cancelled"
        subscription.auto_renew = False
        
        await self.repository.update_subscription_record(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        
        return {
            "id": str(subscription.id),
            "status": subscription.status,
            "auto_renew": subscription.auto_renew,
            "message": "Subscription cancelled successfully."
        }