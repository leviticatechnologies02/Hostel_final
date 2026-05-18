# app/api/v1/plans/routes.py

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from app.dependencies import CurrentUser, DBSession, require_roles
from app.models.plan import Plan, PlanFeature, PlanStatus, DurationType
from app.models.operations import Subscription
from app.schemas.plan import (
    PlanCreateRequest,
    PlanUpdateRequest,
    PlanResponse,
    PlanListResponse,
    PlanFeatureResponse,
    SubscriptionCreateWithPlanRequest,
    SubscriptionAutoFillResponse,
)
from app.services.super_admin_service import SuperAdminAdminCreateRequest
from app.services.subscription_validator import SubscriptionValidator

router = APIRouter()
SuperAdmin = Annotated[CurrentUser, Depends(require_roles("super_admin"))]


# ==================== PLAN CRUD ====================

@router.get("/plans", response_model=PlanListResponse)
async def list_plans(
    _: SuperAdmin,
    db: DBSession,
    status_filter: Optional[str] = Query(None, description="active, inactive"),
    page: int = 1,
    per_page: int = 20,
):
    """List all subscription plans"""
    query = select(Plan)
    
    if status_filter:
        query = query.where(Plan.status == PlanStatus(status_filter))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = int(total_result.scalar() or 0)
    
    # Get paginated results
    query = query.order_by(Plan.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    plans = list(result.scalars().all())
    
    # Load features for each plan
    items = []
    for plan in plans:
        features_result = await db.execute(
            select(PlanFeature).where(PlanFeature.plan_id == plan.id)
            .order_by(PlanFeature.sort_order)
        )
        features = list(features_result.scalars().all())
        
        items.append(PlanResponse(
            id=str(plan.id),
            name=plan.name,
            code=plan.code,
            description=plan.description,
            price_monthly=float(plan.price_monthly),
            price_yearly=float(plan.price_yearly),
            duration_type=plan.duration_type.value,
            duration_days=plan.duration_days,
            hostel_limit=plan.hostel_limit,
            admin_limit=plan.admin_limit,
            auto_renew_allowed=plan.auto_renew_allowed,
            status=plan.status.value,
            features=[PlanFeatureResponse(
                id=str(f.id),
                feature_name=f.feature_name,
                feature_value=f.feature_value,
                is_included=f.is_included,
                sort_order=f.sort_order
            ) for f in features],
            created_at=plan.created_at,
            updated_at=plan.updated_at
        ))
    
    return PlanListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/plans", response_model=PlanResponse, status_code=201)
async def create_plan(
    payload: PlanCreateRequest,
    _: SuperAdmin,
    db: DBSession,
):
    """Create a new subscription plan"""
    # Check if code already exists
    existing = await db.execute(select(Plan).where(Plan.code == payload.code))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plan with code '{payload.code}' already exists"
        )
    
    # Create plan
    plan = Plan(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        price_monthly=payload.price_monthly,
        price_yearly=payload.price_yearly,
        duration_type=DurationType(payload.duration_type),
        duration_days=payload.duration_days,
        hostel_limit=payload.hostel_limit,
        admin_limit=payload.admin_limit,
        auto_renew_allowed=payload.auto_renew_allowed,
        status=PlanStatus(payload.status),
    )
    db.add(plan)
    await db.flush()
    
    # Add features
    for i, feat in enumerate(payload.features):
        feature = PlanFeature(
            plan_id=plan.id,
            feature_name=feat.feature_name,
            feature_value=feat.feature_value,
            is_included=feat.is_included,
            sort_order=i,
        )
        db.add(feature)
    
    await db.commit()
    await db.refresh(plan)
    
    # Load features
    features_result = await db.execute(
        select(PlanFeature).where(PlanFeature.plan_id == plan.id)
        .order_by(PlanFeature.sort_order)
    )
    features = list(features_result.scalars().all())
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        code=plan.code,
        description=plan.description,
        price_monthly=float(plan.price_monthly),
        price_yearly=float(plan.price_yearly),
        duration_type=plan.duration_type.value,
        duration_days=plan.duration_days,
        hostel_limit=plan.hostel_limit,
        admin_limit=plan.admin_limit,
        auto_renew_allowed=plan.auto_renew_allowed,
        status=plan.status.value,
        features=[PlanFeatureResponse(
            id=str(f.id),
            feature_name=f.feature_name,
            feature_value=f.feature_value,
            is_included=f.is_included,
            sort_order=f.sort_order
        ) for f in features],
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    _: SuperAdmin,
    db: DBSession,
):
    """Get a single plan by ID"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    features_result = await db.execute(
        select(PlanFeature).where(PlanFeature.plan_id == plan.id)
        .order_by(PlanFeature.sort_order)
    )
    features = list(features_result.scalars().all())
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        code=plan.code,
        description=plan.description,
        price_monthly=float(plan.price_monthly),
        price_yearly=float(plan.price_yearly),
        duration_type=plan.duration_type.value,
        duration_days=plan.duration_days,
        hostel_limit=plan.hostel_limit,
        admin_limit=plan.admin_limit,
        auto_renew_allowed=plan.auto_renew_allowed,
        status=plan.status.value,
        features=[PlanFeatureResponse(
            id=str(f.id),
            feature_name=f.feature_name,
            feature_value=f.feature_value,
            is_included=f.is_included,
            sort_order=f.sort_order
        ) for f in features],
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    payload: PlanUpdateRequest,
    _: SuperAdmin,
    db: DBSession,
):
    """Update an existing plan"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "duration_type" and value:
            setattr(plan, field, DurationType(value))
        elif field == "status" and value:
            setattr(plan, field, PlanStatus(value))
        elif field != "features" and value is not None:
            setattr(plan, field, value)
    
    # Update features if provided
    if payload.features is not None:
        # Delete existing features
        await db.execute(
            select(PlanFeature).where(PlanFeature.plan_id == plan.id)
        )
        await db.execute(
            PlanFeature.__table__.delete().where(PlanFeature.plan_id == plan.id)
        )
        
        # Add new features
        for i, feat in enumerate(payload.features):
            feature = PlanFeature(
                plan_id=plan.id,
                feature_name=feat.feature_name,
                feature_value=feat.feature_value,
                is_included=feat.is_included,
                sort_order=i,
            )
            db.add(feature)
    
    await db.commit()
    await db.refresh(plan)
    
    # Load features for response
    features_result = await db.execute(
        select(PlanFeature).where(PlanFeature.plan_id == plan.id)
        .order_by(PlanFeature.sort_order)
    )
    features = list(features_result.scalars().all())
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        code=plan.code,
        description=plan.description,
        price_monthly=float(plan.price_monthly),
        price_yearly=float(plan.price_yearly),
        duration_type=plan.duration_type.value,
        duration_days=plan.duration_days,
        hostel_limit=plan.hostel_limit,
        admin_limit=plan.admin_limit,
        auto_renew_allowed=plan.auto_renew_allowed,
        status=plan.status.value,
        features=[PlanFeatureResponse(
            id=str(f.id),
            feature_name=f.feature_name,
            feature_value=f.feature_value,
            is_included=f.is_included,
            sort_order=f.sort_order
        ) for f in features],
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: str,
    _: SuperAdmin,
    db: DBSession,
):
    """Delete a plan (only if not used in any subscription)"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Check if plan is used in any subscription
    sub_result = await db.execute(
        select(Subscription).where(Subscription.plan_id == plan_id).limit(1)
    )
    if sub_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete plan that is used in existing subscriptions. Deactivate it instead."
        )
    
    await db.delete(plan)
    await db.commit()


@router.patch("/plans/{plan_id}/toggle-status", response_model=PlanResponse)
async def toggle_plan_status(
    plan_id: str,
    _: SuperAdmin,
    db: DBSession,
):
    """Toggle plan status (active/inactive)"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan.status = PlanStatus.INACTIVE if plan.status == PlanStatus.ACTIVE else PlanStatus.ACTIVE
    await db.commit()
    await db.refresh(plan)
    
    return await get_plan(plan_id, _, db)


# ==================== PLAN AUTO-FILL FOR SUBSCRIPTIONS ====================

@router.get("/plans/{plan_id}/auto-fill")
async def get_plan_auto_fill(
    plan_id: str,
    start_date: str,
    _: SuperAdmin,
    db: DBSession,
) -> SubscriptionAutoFillResponse:
    """
    Get auto-fill data for a plan.
    Returns calculated end_date, pricing, and limits based on the selected plan.
    """
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    try:
        start = date.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    # Calculate end date based on duration days
    end_date = start + timedelta(days=plan.duration_days)
    
    # Load features
    features_result = await db.execute(
        select(PlanFeature).where(PlanFeature.plan_id == plan.id)
        .order_by(PlanFeature.sort_order)
    )
    features = list(features_result.scalars().all())
    
    return SubscriptionAutoFillResponse(
        plan_id=str(plan.id),
        plan_name=plan.name,
        plan_code=plan.code,
        price_monthly=float(plan.price_monthly),
        price_yearly=float(plan.price_yearly),
        duration_days=plan.duration_days,
        duration_type=plan.duration_type.value,
        end_date=end_date.isoformat(),
        hostel_limit=plan.hostel_limit,
        admin_limit=plan.admin_limit,
        auto_renew_allowed=plan.auto_renew_allowed,
        features=[PlanFeatureResponse(
            id=str(f.id),
            feature_name=f.feature_name,
            feature_value=f.feature_value,
            is_included=f.is_included,
            sort_order=f.sort_order
        ) for f in features]
    )


# ==================== UPDATED SUBSCRIPTION ENDPOINTS ====================

@router.post("/subscriptions/from-plan", response_model=dict)
async def create_subscription_from_plan(
    payload: SubscriptionCreateWithPlanRequest,
    _: SuperAdmin,
    db: DBSession,
):
    """
    Create a subscription using a plan.
    Price, duration, and end date are auto-filled from the plan.
    """
    from app.services.super_admin_service import SuperAdminService
    
    # Get the plan
    plan_result = await db.execute(select(Plan).where(Plan.id == payload.plan_id))
    plan = plan_result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if plan.status != PlanStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Plan is not active")
    
    try:
        start = date.fromisoformat(payload.start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    # Calculate end date
    end = start + timedelta(days=plan.duration_days)
    
    # Use monthly price for the subscription
    price = plan.price_monthly if plan.duration_type != DurationType.YEARLY else plan.price_yearly / 12
    
    # Create subscription using existing super admin service
    service = SuperAdminService(db)
    
    # Assuming SuperAdminService has a method to create subscription
    # You'll need to ensure this method exists or adapt accordingly
    subscription = await service.create_subscription(
        payload=SuperAdminSubscriptionCreateRequest(
            hostel_id=payload.hostel_id,
            tier=plan.name,
            price_monthly=price,
            start_date=start,
            end_date=end,
            auto_renew=payload.auto_renew,
            status="active"
        )
    )
    
    # Link the plan to the subscription
    if subscription and hasattr(subscription, 'id'):
        sub = await db.execute(
            select(Subscription).where(Subscription.id == subscription.id)
        )
        sub_obj = sub.scalar_one_or_none()
        if sub_obj:
            sub_obj.plan_id = plan.id
            await db.commit()
    
    return {
        "message": "Subscription created successfully",
        "subscription": subscription,
        "plan_applied": {
            "plan_name": plan.name,
            "duration_days": plan.duration_days,
            "hostel_limit": plan.hostel_limit,
            "admin_limit": plan.admin_limit
        }
    }


@router.get("/hostels/{hostel_id}/subscription-limit-status")
async def check_hostel_subscription_limit(
    hostel_id: str,
    _: SuperAdmin,
    db: DBSession,
):
    """
    Check if a hostel has reached its subscription plan limits.
    """
    from sqlalchemy import select, func
    from app.models.operations import Subscription
    from app.models.hostel import Hostel
    
    # Get the active subscription for this hostel
    sub_result = await db.execute(
        select(Subscription)
        .where(
            Subscription.hostel_id == hostel_id,
            Subscription.status == "active"
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = sub_result.scalar_one_or_none()
    
    if not subscription:
        return {
            "has_active_subscription": False,
            "message": "No active subscription found for this hostel"
        }
    
    # Get the associated plan
    plan_result = await db.execute(select(Plan).where(Plan.id == subscription.plan_id))
    plan = plan_result.scalar_one_or_none()
    
    if not plan or plan.hostel_limit == -1:
        return {
            "has_active_subscription": True,
            "hostel_limit": plan.hostel_limit if plan else "unlimited",
            "message": "No limits enforced (unlimited plan)"
        }
    
    # Count hostels assigned to this admin (if this is a multi-hostel scenario)
    from app.models.hostel import AdminHostelMapping
    admin_hostel_count = await db.execute(
        select(func.count()).select_from(AdminHostelMapping)
        .where(AdminHostelMapping.hostel_id == hostel_id)
    )
    current_count = admin_hostel_count.scalar() or 0
    
    is_at_limit = current_count >= plan.hostel_limit
    
    return {
        "has_active_subscription": True,
        "hostel_limit": plan.hostel_limit,
        "current_hostel_count": current_count,
        "is_at_limit": is_at_limit,
        "remaining_slots": max(0, plan.hostel_limit - current_count),
        "message": f"Hostel limit: {current_count}/{plan.hostel_limit}"
    }