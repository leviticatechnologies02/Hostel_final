# app/api/v1/reports/routes.py
"""
Reports routes for Super Admin reporting module.
Provides comprehensive analytics and reporting endpoints.
"""

from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from datetime import date, datetime, timedelta
import csv
import io
import json

from app.dependencies import CurrentUser, DBSession, require_roles
from app.schemas.reports import (
    ReportFilters,
    FinancialReportResponse,
    BookingReportResponse,
    HostelPerformanceResponse,
    OccupancyReportResponse,
    ComplaintReportResponse,
    DashboardSummaryResponse,
    ExportRequest,
)
from app.services.reports_service import ReportsService

router = APIRouter()
SuperAdmin = Annotated[CurrentUser, Depends(require_roles("super_admin"))]


# ==================== DASHBOARD ====================

@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    _: SuperAdmin,
    db: DBSession,
):
    """
    **Super Admin Dashboard Summary.**
    
    Returns key metrics for the platform overview:
    - Total and active hostels count
    - Student statistics
    - Booking statistics
    - Monthly revenue with growth percentage
    - Overall occupancy rate
    - Complaint resolution rate
    - Recent activity feed
    """
    service = ReportsService(db)
    return await service.get_dashboard_summary()


# ==================== FINANCIAL REPORTS ====================

@router.get("/financial", response_model=FinancialReportResponse)
async def get_financial_report(
    _: SuperAdmin,
    db: DBSession,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    hostel_id: Optional[str] = Query(None, description="Filter by specific hostel ID"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
):
    """
    **Generate Financial Report.**
    """
    filters = ReportFilters(
        start_date=start_date,
        end_date=end_date,
        hostel_id=hostel_id,
        city=city,
        state=state
    )
    service = ReportsService(db)
    return await service.get_financial_report(filters)


# ==================== BOOKING REPORTS ====================

@router.get("/bookings", response_model=BookingReportResponse)
async def get_booking_report(
    _: SuperAdmin,
    db: DBSession,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    hostel_id: Optional[str] = Query(None, description="Filter by specific hostel ID"),
):
    """
    **Generate Booking Analytics Report.**
    """
    filters = ReportFilters(
        start_date=start_date,
        end_date=end_date,
        hostel_id=hostel_id
    )
    service = ReportsService(db)
    return await service.get_booking_report(filters)


# ==================== HOSTEL PERFORMANCE REPORT ====================

@router.get("/hostel-performance", response_model=HostelPerformanceResponse)
async def get_hostel_performance_report(
    _: SuperAdmin,
    db: DBSession,
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    hostel_id: Optional[str] = Query(None, description="Filter by specific hostel ID"),
):
    """
    **Generate Hostel Performance Report.**
    """
    from datetime import timedelta as td
    
    if hostel_id or city or state:
        filters = ReportFilters(
            start_date=date.today() - td(days=30),
            end_date=date.today(),
            hostel_id=hostel_id,
            city=city,
            state=state
        )
    else:
        filters = None
    
    service = ReportsService(db)
    return await service.get_hostel_performance_report(filters)


# ==================== OCCUPANCY REPORT ====================

@router.get("/occupancy", response_model=OccupancyReportResponse)
async def get_occupancy_report(
    _: SuperAdmin,
    db: DBSession,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    hostel_id: Optional[str] = Query(None, description="Filter by specific hostel ID"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
):
    """
    **Generate Occupancy Report.**
    """
    filters = ReportFilters(
        start_date=start_date,
        end_date=end_date,
        hostel_id=hostel_id,
        city=city,
        state=state
    )
    service = ReportsService(db)
    return await service.get_occupancy_report(filters)


# ==================== COMPLAINT REPORT ====================

@router.get("/complaints", response_model=ComplaintReportResponse)
async def get_complaint_report(
    _: SuperAdmin,
    db: DBSession,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    hostel_id: Optional[str] = Query(None, description="Filter by specific hostel ID"),
):
    """
    **Generate Complaint Analytics Report.**
    """
    filters = ReportFilters(
        start_date=start_date,
        end_date=end_date,
        hostel_id=hostel_id
    )
    service = ReportsService(db)
    return await service.get_complaint_report(filters)


# ==================== EXPORT ENDPOINTS ====================

@router.post("/export")
async def export_report(
    request: ExportRequest,
    _: SuperAdmin,
    db: DBSession,
):
    """
    **Export Report to CSV or JSON.**
    """
    service = ReportsService(db)
    
    # Generate report data based on type
    if request.report_type == "financial":
        result = await service.get_financial_report(request.filters)
    elif request.report_type == "booking":
        result = await service.get_booking_report(request.filters)
    elif request.report_type == "occupancy":
        result = await service.get_occupancy_report(request.filters)
    elif request.report_type == "hostel_performance":
        result = await service.get_hostel_performance_report(request.filters)
    elif request.report_type == "complaints":
        result = await service.get_complaint_report(request.filters)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {request.report_type}")
    
    # Convert to dict for export
    if hasattr(result, 'model_dump'):
        export_data = result.model_dump()
    elif hasattr(result, 'dict'):
        export_data = result.dict()
    else:
        export_data = result
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{request.report_type}_report_{timestamp}.{request.format}"
    
    if request.format == "json":
        content = json.dumps(export_data, indent=2, default=str)
        media_type = "application/json"
        
    elif request.format == "csv":
        output = io.StringIO()
        
        def safe_str(value):
            if value is None:
                return ''
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            if isinstance(value, float):
                return f"{value:.2f}"
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)
        
        # Extract list data based on report type
        flat_data = []
        
        if request.report_type == "financial":
            flat_data = export_data.get("revenue_by_hostel", [])
            if not flat_data:
                flat_data = export_data.get("period_revenue", [])
        elif request.report_type == "booking":
            flat_data = export_data.get("status_distribution", [])
            if not flat_data:
                flat_data = export_data.get("volume_over_time", [])
        elif request.report_type == "occupancy":
            flat_data = export_data.get("daily_occupancy", [])
        elif request.report_type == "hostel_performance":
            flat_data = export_data.get("hostels", [])
        elif request.report_type == "complaints":
            flat_data = export_data.get("by_priority", [])
            if not flat_data:
                flat_data = export_data.get("by_category", [])
        
        # Ensure flat_data is a list
        if not isinstance(flat_data, list):
            flat_data = [flat_data] if flat_data else []
        
        # Fallback to summary if no list data
        if not flat_data:
            summary = export_data.get("summary", {})
            if summary:
                flat_data = [summary]
            else:
                flat_data = [{"message": "No data available for export"}]
        
        # Get fieldnames from first item
        if flat_data:
            first_item = flat_data[0]
            if isinstance(first_item, dict):
                fieldnames = list(first_item.keys())
            else:
                if hasattr(first_item, 'model_dump'):
                    fieldnames = list(first_item.model_dump().keys())
                elif hasattr(first_item, 'dict'):
                    fieldnames = list(first_item.dict().keys())
                else:
                    fieldnames = [k for k in dir(first_item) if not k.startswith('_') and not callable(getattr(first_item, k))]
        else:
            fieldnames = ["message"]
        
        # Filter out internal fields
        exclude = {'model_config', 'model_fields', 'model_computed_fields'}
        fieldnames = [f for f in fieldnames if f not in exclude]
        
        if not fieldnames:
            fieldnames = ['message']
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for item in flat_data:
            # Convert item to dict
            if isinstance(item, dict):
                row = item
            else:
                if hasattr(item, 'model_dump'):
                    row = item.model_dump()
                elif hasattr(item, 'dict'):
                    row = item.dict()
                else:
                    row = {}
                    for field in fieldnames:
                        try:
                            row[field] = safe_str(getattr(item, field, ''))
                        except:
                            row[field] = ''
            
            # Build CSV row
            csv_row = {}
            for field in fieldnames:
                value = row.get(field)
                csv_row[field] = safe_str(value)
            
            writer.writerow(csv_row)
        
        content = output.getvalue()
        media_type = "text/csv"
        
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")
    
    # Ensure content is a string
    if not isinstance(content, str):
        content = str(content)
    
    encoded_content = content.encode('utf-8')
    
    return Response(
        content=encoded_content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(encoded_content))
        }
    )


# ==================== REPORT METADATA ====================

@router.get("/available-reports")
async def get_available_reports(_: SuperAdmin):
    """
    **List available report types and their schemas.**
    """
    return {
        "reports": [
            {
                "id": "financial",
                "name": "Financial Report",
                "description": "Revenue analysis including advances, monthly rents, and payment type breakdown",
                "required_filters": ["start_date", "end_date"],
                "optional_filters": ["hostel_id", "city", "state"],
                "export_formats": ["json", "csv"]
            },
            {
                "id": "booking",
                "name": "Booking Analytics Report",
                "description": "Booking volume, status distribution, lead times, and cancellation rates",
                "required_filters": ["start_date", "end_date"],
                "optional_filters": ["hostel_id"],
                "export_formats": ["json", "csv"]
            },
            {
                "id": "hostel_performance",
                "name": "Hostel Performance Report",
                "description": "Occupancy rates, booking counts, revenue, and ratings per hostel",
                "required_filters": [],
                "optional_filters": ["hostel_id", "city", "state"],
                "export_formats": ["json", "csv"]
            },
            {
                "id": "occupancy",
                "name": "Occupancy Report",
                "description": "Daily bed occupancy tracking and trends",
                "required_filters": ["start_date", "end_date"],
                "optional_filters": ["hostel_id", "city", "state"],
                "export_formats": ["json", "csv"]
            },
            {
                "id": "complaints",
                "name": "Complaint Analytics Report",
                "description": "Complaint distribution by priority, category, and SLA compliance",
                "required_filters": ["start_date", "end_date"],
                "optional_filters": ["hostel_id"],
                "export_formats": ["json", "csv"]
            }
        ]
    }


# ==================== SEARCH & FILTER HELPERS ====================

@router.get("/cities")
async def get_report_cities(
    _: SuperAdmin,
    db: DBSession,
):
    """Get list of cities with hostels for report filtering."""
    from sqlalchemy import select, distinct
    from app.models.hostel import Hostel, HostelStatus
    
    result = await db.execute(
        select(distinct(Hostel.city))
        .where(Hostel.status == HostelStatus.ACTIVE)
        .order_by(Hostel.city)
    )
    return {"cities": [row for row in result.scalars().all() if row]}


@router.get("/states")
async def get_report_states(
    _: SuperAdmin,
    db: DBSession,
):
    """Get list of states with hostels for report filtering."""
    from sqlalchemy import select, distinct
    from app.models.hostel import Hostel, HostelStatus
    
    result = await db.execute(
        select(distinct(Hostel.state))
        .where(Hostel.status == HostelStatus.ACTIVE)
        .order_by(Hostel.state)
    )
    return {"states": [row for row in result.scalars().all() if row]}


@router.get("/test")
async def test_endpoint(_: SuperAdmin):
    """Test endpoint to verify router is mounted."""
    return {"status": "ok", "message": "Reports router is working"}


@router.get("/ping")
async def ping(_: SuperAdmin):
    """Test endpoint to verify reports router is working."""
    return {"status": "ok", "message": "Reports API is accessible"}