# app/models/plan.py
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.operations import Subscription


class DurationType(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class PlanStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Plan(BaseModel):
    """Subscription plan model - reusable plan templates"""
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    price_yearly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    duration_type: Mapped[DurationType] = mapped_column(Enum(DurationType), default=DurationType.MONTHLY)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    hostel_limit: Mapped[int] = mapped_column(Integer, default=1)  # -1 for unlimited
    admin_limit: Mapped[int] = mapped_column(Integer, default=1)   # -1 for unlimited
    auto_renew_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus), default=PlanStatus.ACTIVE)
    
    # Features (many-to-many or simple list)
    features: Mapped[list[PlanFeature]] = relationship(
        "PlanFeature", back_populates="plan", cascade="all, delete-orphan"
    )
    
    # Subscriptions using this plan
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="plan"
    )


class PlanFeature(BaseModel):
    """Individual features included in a plan"""
    __tablename__ = "plan_features"

    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_included: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    plan: Mapped[Plan] = relationship("Plan", back_populates="features")