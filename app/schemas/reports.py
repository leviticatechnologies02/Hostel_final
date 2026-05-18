# FILE: app/schemas/reports.py
"""
Report schemas for Super Admin reporting module.
Provides data aggregation for financial, operational, and booking reports.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ==================== BASE / COMMON SCHEMAS ====================

class DateRangeFilter(BaseModel):
    """Date range filter for reports."""
    start_date: date = Field(..., description="Start date for report (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date for report (YYYY-MM-DD)")
    
    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        data = info.data
        start_date = data.get("start_date")
        if start_date and v < start_date:
            raise ValueError("end_date must be after start_date")
        return v


class ReportFilters(BaseModel):
    """Common report filters."""
    start_date: date = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (YYYY-MM-DD)")
    hostel_id: Optional[str] = Field(None, description="Filter by specific hostel")
    city: Optional[str] = Field(None, description="Filter by city")
    state: Optional[str] = Field(None, description="Filter by state")
    status: Optional[str] = Field(None, description="Filter by status")
    
    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        data = info.data
        start_date = data.get("start_date")
        if start_date and v < start_date:
            raise ValueError("end_date must be after start_date")
        return v


# ==================== FINANCIAL REPORTS ====================

class RevenueSummaryItem(BaseModel):
    """Revenue summary by day/month."""
    period: str = Field(..., description="Date period (YYYY-MM-DD or YYYY-MM)")
    total_revenue: float = Field(0.0, description="Total revenue for period")
    booking_advances: float = Field(0.0, description="Booking advance payments")
    monthly_rents: float = Field(0.0, description="Monthly rent collections")
    refunds: float = Field(0.0, description="Refunded amounts")
    net_revenue: float = Field(0.0, description="Net revenue after refunds")
    transaction_count: int = Field(0, description="Number of transactions")


class RevenueByHostelItem(BaseModel):
    """Revenue breakdown by hostel."""
    hostel_id: str
    hostel_name: str
    city: str
    total_revenue: float
    advance_payments: float
    monthly_rent_collections: float
    active_bookings: int
    checked_in_students: int
    occupancy_rate: float = Field(0.0, description="Percentage of occupied beds")


class RevenueByPaymentType(BaseModel):
    """Revenue breakdown by payment type."""
    payment_type: str
    amount: float
    percentage: float
    transaction_count: int


class FinancialReportResponse(BaseModel):
    """Complete financial report response."""
    summary: dict = Field(..., description="Summary statistics")
    period_revenue: List[RevenueSummaryItem] = Field(default_factory=list)
    revenue_by_hostel: List[RevenueByHostelItem] = Field(default_factory=list)
    revenue_by_payment_type: List[RevenueByPaymentType] = Field(default_factory=list)
    total_revenue: float = 0.0
    total_advances: float = 0.0
    total_monthly_rent: float = 0.0
    total_refunds: float = 0.0
    net_revenue: float = 0.0
    transaction_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== BOOKING REPORTS ====================

class BookingStatusCount(BaseModel):
    """Count of bookings by status."""
    status: str
    count: int
    percentage: float


class BookingVolumeItem(BaseModel):
    """Booking volume over time."""
    period: str
    new_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    net_change: int


class BookingReportResponse(BaseModel):
    """Complete booking report response."""
    summary: dict
    status_distribution: List[BookingStatusCount]
    volume_over_time: List[BookingVolumeItem]
    average_lead_time_days: float
    average_stay_duration_days: float
    cancellation_rate: float
    total_bookings: int
    generated_at: datetime


# ==================== HOSTEL PERFORMANCE REPORTS ====================

class HostelPerformanceItem(BaseModel):
    """Performance metrics for a single hostel."""
    hostel_id: str
    hostel_name: str
    city: str
    status: str
    total_rooms: int
    total_beds: int
    occupied_beds: int
    available_beds: int
    occupancy_rate: float
    total_bookings: int
    active_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_revenue: float
    average_rating: float
    total_reviews: int


class HostelPerformanceResponse(BaseModel):
    """Hostel performance report response."""
    summary: dict
    hostels: List[HostelPerformanceItem]
    city_wise_summary: List[dict]
    status_wise_summary: List[dict]
    generated_at: datetime


# ==================== OCCUPANCY REPORTS ====================

class OccupancyItem(BaseModel):
    """Occupancy data point."""
    date: date
    total_beds: int
    occupied_beds: int
    available_beds: int
    occupancy_rate: float


class OccupancyReportResponse(BaseModel):
    """Occupancy report response."""
    summary: dict
    daily_occupancy: List[OccupancyItem]
    peak_occupancy_date: Optional[date] = None
    peak_occupancy_rate: float = 0.0
    average_occupancy_rate: float = 0.0
    generated_at: datetime


# ==================== COMPLAINT REPORT ====================

class ComplaintSummary(BaseModel):
    """Complaint statistics."""
    priority: str
    count: int
    resolved_count: int
    pending_count: int
    resolution_rate: float
    average_resolution_hours: float


class ComplaintReportResponse(BaseModel):
    """Complaint report response."""
    summary: dict
    by_priority: List[ComplaintSummary]
    by_category: List[dict]
    by_hostel: List[dict]
    sla_breached_count: int
    sla_compliant_count: int
    generated_at: datetime


# ==================== STUDENT REPORT ====================

class StudentDemographics(BaseModel):
    """Student demographics data."""
    total_students: int
    active_students: int
    by_gender: dict
    by_hostel: List[dict]
    by_city: List[dict]
    new_students_in_period: int


class StudentReportResponse(BaseModel):
    """Student report response."""
    summary: StudentDemographics
    attendance_summary: dict
    payment_compliance: dict
    generated_at: datetime


# ==================== DASHBOARD SUMMARY ====================

class DashboardSummaryResponse(BaseModel):
    """Super admin dashboard summary."""
    total_hostels: int
    active_hostels: int
    pending_approval_hostels: int
    total_students: int
    active_students: int
    total_bookings: int
    pending_bookings: int
    total_revenue_month: float
    revenue_growth_percent: float
    occupancy_rate_avg: float
    complaint_resolution_rate: float
    recent_activity: List[dict]
    generated_at: datetime


# ==================== EXPORT FORMATS ====================

class ExportRequest(BaseModel):
    """Export request model."""
    report_type: str = Field(..., description="financial, booking, occupancy, hostel_performance, complaints, students")
    format: str = Field(default="json", description="json, csv, excel")
    filters: ReportFilters
    include_details: bool = Field(default=False, description="Include detailed line items")


class ExportResponse(BaseModel):
    """Export response model."""
    download_url: str
    file_name: str
    expires_at: datetime
    size_bytes: int