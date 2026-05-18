# app/schemas/plan.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import APIModel, TimestampedResponse


class PlanFeatureCreate(BaseModel):
    feature_name: str = Field(min_length=2, max_length=100)
    feature_value: Optional[str] = Field(None, max_length=255)
    is_included: bool = True
    sort_order: int = 0


class PlanFeatureResponse(APIModel):
    id: str
    feature_name: str
    feature_value: Optional[str] = None
    is_included: bool
    sort_order: int


class PlanCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=50, pattern=r'^[A-Z0-9_]+$')
    description: Optional[str] = Field(None, max_length=500)
    price_monthly: float = Field(ge=0, default=0)
    price_yearly: float = Field(ge=0, default=0)
    duration_type: str = Field(default="monthly", pattern="^(monthly|quarterly|yearly|custom)$")
    duration_days: int = Field(ge=1, le=3650, default=30)
    hostel_limit: int = Field(ge=-1, default=1)  # -1 = unlimited
    admin_limit: int = Field(ge=-1, default=1)   # -1 = unlimited
    auto_renew_allowed: bool = True
    status: str = Field(default="active", pattern="^(active|inactive)$")
    features: List[PlanFeatureCreate] = Field(default_factory=list)


class PlanUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price_monthly: Optional[float] = Field(None, ge=0)
    price_yearly: Optional[float] = Field(None, ge=0)
    duration_type: Optional[str] = Field(None, pattern="^(monthly|quarterly|yearly|custom)$")
    duration_days: Optional[int] = Field(None, ge=1, le=3650)
    hostel_limit: Optional[int] = Field(None, ge=-1)
    admin_limit: Optional[int] = Field(None, ge=-1)
    auto_renew_allowed: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
    features: Optional[List[PlanFeatureCreate]] = None


class PlanResponse(TimestampedResponse):
    name: str
    code: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    duration_type: str
    duration_days: int
    hostel_limit: int
    admin_limit: int
    auto_renew_allowed: bool
    status: str
    features: List[PlanFeatureResponse] = []


class PlanListResponse(BaseModel):
    items: List[PlanResponse]
    total: int
    page: int
    per_page: int


# Updated subscription schemas
class SubscriptionCreateWithPlanRequest(BaseModel):
    hostel_id: str
    plan_id: str
    start_date: str  # YYYY-MM-DD
    auto_renew: bool = True
    
    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, v: str) -> str:
        from datetime import date
        try:
            start = date.fromisoformat(v)
            if start < date.today():
                raise ValueError("Start date cannot be in the past")
            return v
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")


class SubscriptionAutoFillResponse(BaseModel):
    """Response when selecting a plan - auto-fills subscription details"""
    plan_id: str
    plan_name: str
    plan_code: str
    price_monthly: float
    price_yearly: float
    duration_days: int
    duration_type: str
    end_date: str  # Calculated from start_date + duration_days
    hostel_limit: int
    admin_limit: int
    auto_renew_allowed: bool
    features: List[PlanFeatureResponse]