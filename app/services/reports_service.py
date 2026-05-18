# app/services/reports_service.py - Fixed version with missing imports

"""
Reports service for Super Admin reporting module.
Handles data aggregation, filtering, and report generation.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func as sql_func

from app.models.hostel import Hostel, HostelStatus
from app.models.booking import Booking, BookingStatus, BookingMode
from app.models.payment import Payment
from app.models.student import Student, StudentStatus
from app.models.user import User, UserRole
from app.models.operations import Complaint, Review
from app.models.room import Bed, BedStatus, Room
from app.schemas.reports import (
    ReportFilters,
    FinancialReportResponse,
    RevenueSummaryItem,
    RevenueByHostelItem,
    RevenueByPaymentType,
    BookingReportResponse,
    BookingStatusCount,
    BookingVolumeItem,
    HostelPerformanceResponse,
    HostelPerformanceItem,
    OccupancyReportResponse,
    OccupancyItem,
    ComplaintReportResponse,
    ComplaintSummary,
    DashboardSummaryResponse,
)


class ReportsService:
    """Service for generating reports for super admin."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ==================== HELPER METHODS ====================
    
    async def _get_active_hostel_ids(self, filters: ReportFilters = None) -> List[str]:
        """Get list of active hostel IDs with optional filters."""
        query = select(Hostel.id).where(
            Hostel.status == HostelStatus.ACTIVE,
            Hostel.is_public == True
        )
        
        if filters:
            if filters.city:
                query = query.where(Hostel.city.ilike(f"%{filters.city}%"))
            if filters.state:
                query = query.where(Hostel.state.ilike(f"%{filters.state}%"))
            if filters.hostel_id:
                query = query.where(Hostel.id == filters.hostel_id)
        
        result = await self.session.execute(query)
        return [str(row) for row in result.scalars().all()]
    
    async def _get_date_filter_conditions(self, table, date_column, filters: ReportFilters):
        """Get date filter conditions for queries."""
        conditions = []
        if filters.start_date:
            conditions.append(date_column >= filters.start_date)
        if filters.end_date:
            conditions.append(date_column <= filters.end_date)
        if filters.hostel_id:
            if hasattr(table, "hostel_id"):
                conditions.append(getattr(table, "hostel_id") == filters.hostel_id)
        return conditions
    
    # ==================== FINANCIAL REPORTS ====================
    
    async def get_financial_report(self, filters: ReportFilters) -> FinancialReportResponse:
        """Generate comprehensive financial report."""
        
        # Base conditions for payments
        payment_conditions = [
            Payment.status == "captured"
        ]
        payment_conditions.extend(await self._get_date_filter_conditions(Payment, Payment.created_at, filters))
        
        # Add hostel filter with join if needed
        query = select(Payment).where(and_(*payment_conditions))
        if filters.hostel_id:
            query = query.where(Payment.hostel_id == filters.hostel_id)
        
        result = await self.session.execute(query)
        payments = result.scalars().all()
        
        # Calculate totals
        total_revenue = Decimal('0')
        total_advances = Decimal('0')
        total_monthly_rent = Decimal('0')
        total_refunds = Decimal('0')
        transaction_count = 0
        
        for payment in payments:
            amount = Decimal(str(payment.amount))
            total_revenue += amount
            transaction_count += 1
            
            if payment.payment_type == "booking_advance":
                total_advances += amount
            elif payment.payment_type == "monthly_rent":
                total_monthly_rent += amount
        
        net_revenue = total_revenue - total_refunds
        
        # Get daily revenue breakdown
        daily_revenue = await self._get_daily_revenue_breakdown(filters)
        
        # Get revenue by hostel
        revenue_by_hostel = await self._get_revenue_by_hostel(filters)
        
        # Get revenue by payment type
        payment_type_breakdown = await self._get_payment_type_breakdown(filters)
        
        # Summary statistics
        summary = {
            "report_period": f"{filters.start_date} to {filters.end_date}",
            "hostel_filter": filters.hostel_id or "All Hostels",
            "total_hostels_in_report": len(await self._get_active_hostel_ids(filters)),
            "currency": "INR"
        }
        
        return FinancialReportResponse(
            summary=summary,
            period_revenue=daily_revenue,
            revenue_by_hostel=revenue_by_hostel,
            revenue_by_payment_type=payment_type_breakdown,
            total_revenue=float(total_revenue),
            total_advances=float(total_advances),
            total_monthly_rent=float(total_monthly_rent),
            total_refunds=float(total_refunds),
            net_revenue=float(net_revenue),
            transaction_count=transaction_count,
            generated_at=datetime.now()
        )
    
    async def _get_daily_revenue_breakdown(self, filters: ReportFilters) -> List[RevenueSummaryItem]:
        """Get daily revenue breakdown."""
        # Determine grouping (daily or monthly based on date range)
        days = (filters.end_date - filters.start_date).days
        group_by = "day" if days <= 31 else "month"
        
        # Build query
        date_trunc = func.date_trunc(group_by, Payment.created_at).label("period")
        
        query = select(
            date_trunc,
            func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
            func.coalesce(func.sum(case((Payment.payment_type == "booking_advance", Payment.amount), else_=0)), 0).label("booking_advances"),
            func.coalesce(func.sum(case((Payment.payment_type == "monthly_rent", Payment.amount), else_=0)), 0).label("monthly_rents"),
            func.count(Payment.id).label("transaction_count")
        ).where(
            Payment.status == "captured",
            Payment.created_at >= filters.start_date,
            Payment.created_at <= filters.end_date
        )
        
        if filters.hostel_id:
            query = query.where(Payment.hostel_id == filters.hostel_id)
        
        query = query.group_by(date_trunc).order_by(date_trunc)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        items = []
        for row in rows:
            period_str = row.period.strftime("%Y-%m-%d") if group_by == "day" else row.period.strftime("%Y-%m")
            items.append(RevenueSummaryItem(
                period=period_str,
                total_revenue=float(row.total_revenue or 0),
                booking_advances=float(row.booking_advances or 0),
                monthly_rents=float(row.monthly_rents or 0),
                refunds=0.0,
                net_revenue=float(row.total_revenue or 0),
                transaction_count=row.transaction_count or 0
            ))
        
        return items
    
    async def _get_revenue_by_hostel(self, filters: ReportFilters) -> List[RevenueByHostelItem]:
        """Get revenue breakdown by hostel."""
        
        query = select(
            Payment.hostel_id,
            Hostel.name.label("hostel_name"),
            Hostel.city,
            func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
            func.coalesce(func.sum(case((Payment.payment_type == "booking_advance", Payment.amount), else_=0)), 0).label("advance_payments"),
            func.coalesce(func.sum(case((Payment.payment_type == "monthly_rent", Payment.amount), else_=0)), 0).label("monthly_rent")
        ).join(
            Hostel, Hostel.id == Payment.hostel_id
        ).where(
            Payment.status == "captured",
            Payment.created_at >= filters.start_date,
            Payment.created_at <= filters.end_date
        )
        
        if filters.hostel_id:
            query = query.where(Payment.hostel_id == filters.hostel_id)
        
        query = query.group_by(Payment.hostel_id, Hostel.name, Hostel.city).order_by(func.sum(Payment.amount).desc())
        
        result = await self.session.execute(query)
        rows = result.all()
        
        items = []
        for row in rows:
            # Get active bookings and checked-in students for this hostel
            booking_count = await self.session.execute(
                select(func.count()).select_from(Booking)
                .where(Booking.hostel_id == row.hostel_id, Booking.status == BookingStatus.CHECKED_IN)
            )
            student_count = await self.session.execute(
                select(func.count()).select_from(Student)
                .where(Student.hostel_id == row.hostel_id, Student.status == StudentStatus.ACTIVE)
            )
            
            # Calculate occupancy rate
            beds_result = await self.session.execute(
                select(func.count()).select_from(Bed)
                .where(Bed.hostel_id == row.hostel_id)
            )
            total_beds = beds_result.scalar() or 1
            
            occupied_beds = await self.session.execute(
                select(func.count()).select_from(Student)
                .where(Student.hostel_id == row.hostel_id, Student.status == StudentStatus.ACTIVE)
            )
            occupied_count = occupied_beds.scalar() or 0
            
            items.append(RevenueByHostelItem(
                hostel_id=str(row.hostel_id),
                hostel_name=row.hostel_name,
                city=row.city,
                total_revenue=float(row.total_revenue or 0),
                advance_payments=float(row.advance_payments or 0),
                monthly_rent_collections=float(row.monthly_rent or 0),
                active_bookings=booking_count.scalar() or 0,
                checked_in_students=student_count.scalar() or 0,
                occupancy_rate=(occupied_count / total_beds * 100) if total_beds > 0 else 0
            ))
        
        return items
    
    async def _get_payment_type_breakdown(self, filters: ReportFilters) -> List[RevenueByPaymentType]:
        """Get revenue breakdown by payment type."""
        
        query = select(
            Payment.payment_type,
            func.coalesce(func.sum(Payment.amount), 0).label("amount"),
            func.count(Payment.id).label("count")
        ).where(
            Payment.status == "captured",
            Payment.created_at >= filters.start_date,
            Payment.created_at <= filters.end_date
        )
        
        if filters.hostel_id:
            query = query.where(Payment.hostel_id == filters.hostel_id)
        
        query = query.group_by(Payment.payment_type)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        total = sum(float(row.amount or 0) for row in rows)
        
        items = []
        for row in rows:
            amount = float(row.amount or 0)
            items.append(RevenueByPaymentType(
                payment_type=row.payment_type.replace("_", " ").title(),
                amount=amount,
                percentage=(amount / total * 100) if total > 0 else 0,
                transaction_count=row.count or 0
            ))
        
        return items
    
    # ==================== BOOKING REPORTS ====================
    
    async def get_booking_report(self, filters: ReportFilters) -> BookingReportResponse:
        """Generate booking analytics report."""
        
        # Base booking query
        booking_query = select(Booking).where(
            Booking.created_at >= filters.start_date,
            Booking.created_at <= filters.end_date
        )
        
        if filters.hostel_id:
            booking_query = booking_query.where(Booking.hostel_id == filters.hostel_id)
        
        result = await self.session.execute(booking_query)
        bookings = result.scalars().all()
        
        total_bookings = len(bookings)
        
        # Status distribution
        status_counts = {}
        for booking in bookings:
            status = booking.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        status_distribution = []
        for status, count in status_counts.items():
            status_distribution.append(BookingStatusCount(
                status=status.replace("_", " ").title(),
                count=count,
                percentage=(count / total_bookings * 100) if total_bookings > 0 else 0
            ))
        
        # Volume over time (group by week)
        volume_over_time = await self._get_booking_volume_over_time(filters)
        
        # Calculate average lead time (days between booking creation and check-in)
        lead_times = []
        stay_durations = []
        cancellation_count = 0
        
        for booking in bookings:
            if booking.check_in_date and booking.created_at:
                lead_time = (booking.check_in_date - booking.created_at.date()).days
                if lead_time >= 0:
                    lead_times.append(lead_time)
            
            if booking.check_in_date and booking.check_out_date:
                duration = (booking.check_out_date - booking.check_in_date).days
                stay_durations.append(duration)
            
            if booking.status == BookingStatus.CANCELLED:
                cancellation_count += 1
        
        avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0
        avg_stay_duration = sum(stay_durations) / len(stay_durations) if stay_durations else 0
        cancellation_rate = (cancellation_count / total_bookings * 100) if total_bookings > 0 else 0
        
        summary = {
            "report_period": f"{filters.start_date} to {filters.end_date}",
            "total_bookings": total_bookings,
            "unique_customers": len(set(b.visitor_id for b in bookings)),
            "daily_avg": round(total_bookings / ((filters.end_date - filters.start_date).days), 2) if (filters.end_date - filters.start_date).days > 0 else total_bookings
        }
        
        return BookingReportResponse(
            summary=summary,
            status_distribution=status_distribution,
            volume_over_time=volume_over_time,
            average_lead_time_days=round(avg_lead_time, 1),
            average_stay_duration_days=round(avg_stay_duration, 1),
            cancellation_rate=round(cancellation_rate, 1),
            total_bookings=total_bookings,
            generated_at=datetime.now()
        )
    
    async def _get_booking_volume_over_time(self, filters: ReportFilters) -> List[BookingVolumeItem]:
        """Get booking volume grouped by week."""
        
        # Group by week
        query = select(
            func.date_trunc('week', Booking.created_at).label("week_start"),
            func.count().label("new_bookings"),
            func.sum(case((Booking.status == BookingStatus.CHECKED_OUT, 1), else_=0)).label("completed"),
            func.sum(case((Booking.status == BookingStatus.CANCELLED, 1), else_=0)).label("cancelled")
        ).where(
            Booking.created_at >= filters.start_date,
            Booking.created_at <= filters.end_date
        )
        
        if filters.hostel_id:
            query = query.where(Booking.hostel_id == filters.hostel_id)
        
        query = query.group_by("week_start").order_by("week_start")
        
        result = await self.session.execute(query)
        rows = result.all()
        
        items = []
        for row in rows:
            week_start = row.week_start
            new_count = row.new_bookings or 0
            completed_count = row.completed or 0
            cancelled_count = row.cancelled or 0
            
            items.append(BookingVolumeItem(
                period=week_start.strftime("%Y-%m-%d"),
                new_bookings=new_count,
                completed_bookings=completed_count,
                cancelled_bookings=cancelled_count,
                net_change=new_count - cancelled_count
            ))
        
        return items
    
    # ==================== HOSTEL PERFORMANCE REPORTS ====================
    
    async def get_hostel_performance_report(self, filters: ReportFilters = None) -> HostelPerformanceResponse:
        """Generate hostel performance report."""
        
        # Get all active hostels
        query = select(Hostel).where(
            Hostel.status == HostelStatus.ACTIVE,
            Hostel.is_public == True
        )
        
        if filters:
            if filters.city:
                query = query.where(Hostel.city.ilike(f"%{filters.city}%"))
            if filters.state:
                query = query.where(Hostel.state.ilike(f"%{filters.state}%"))
            if filters.hostel_id:
                query = query.where(Hostel.id == filters.hostel_id)
        
        result = await self.session.execute(query)
        hostels = result.scalars().all()
        
        performance_items = []
        total_rooms = 0
        total_beds = 0
        total_occupied = 0
        total_revenue = Decimal('0')
        
        for hostel in hostels:
            hostel_id = str(hostel.id)
            
            # Get room counts
            rooms_result = await self.session.execute(
                select(func.count()).select_from(Room).where(Room.hostel_id == hostel_id)
            )
            room_count = rooms_result.scalar() or 0
            
            # Get bed counts
            beds_result = await self.session.execute(
                select(func.count()).select_from(Bed).where(Bed.hostel_id == hostel_id)
            )
            bed_count = beds_result.scalar() or 0
            
            # Get occupied beds (active students)
            occupied_result = await self.session.execute(
                select(func.count()).select_from(Student)
                .where(
                    Student.hostel_id == hostel_id,
                    Student.status == StudentStatus.ACTIVE
                )
            )
            occupied_count = occupied_result.scalar() or 0
            
            # Get booking counts for this hostel
            booking_counts = await self.session.execute(
                select(
                    func.count().filter(Booking.status == BookingStatus.PENDING_APPROVAL).label("pending"),
                    func.count().filter(Booking.status == BookingStatus.APPROVED).label("approved"),
                    func.count().filter(Booking.status == BookingStatus.CHECKED_IN).label("checked_in"),
                    func.count().filter(Booking.status == BookingStatus.CHECKED_OUT).label("completed"),
                    func.count().filter(Booking.status == BookingStatus.CANCELLED).label("cancelled")
                ).where(Booking.hostel_id == hostel_id)
            )
            counts = booking_counts.first()
            
            # Get revenue for this hostel (all time)
            revenue_result = await self.session.execute(
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(
                    Payment.hostel_id == hostel_id,
                    Payment.status == "captured"
                )
            )
            revenue = float(revenue_result.scalar() or 0)
            
            # Get average rating
            rating_result = await self.session.execute(
                select(func.avg(Review.overall_rating))
                .where(Review.hostel_id == hostel_id, Review.is_published == True)
            )
            avg_rating = rating_result.scalar() or 0
            
            total_rooms += room_count
            total_beds += bed_count
            total_occupied += occupied_count
            total_revenue += Decimal(str(revenue))
            
            total_bookings = (counts.pending or 0) + (counts.approved or 0) + (counts.checked_in or 0) + (counts.completed or 0)
            active_bookings = (counts.approved or 0) + (counts.checked_in or 0)
            
            performance_items.append(HostelPerformanceItem(
                hostel_id=hostel_id,
                hostel_name=hostel.name,
                city=hostel.city,
                status=hostel.status.value,
                total_rooms=room_count,
                total_beds=bed_count,
                occupied_beds=occupied_count,
                available_beds=bed_count - occupied_count,
                occupancy_rate=(occupied_count / bed_count * 100) if bed_count > 0 else 0,
                total_bookings=total_bookings,
                active_bookings=active_bookings,
                completed_bookings=counts.completed or 0,
                cancelled_bookings=counts.cancelled or 0,
                total_revenue=revenue,
                average_rating=float(avg_rating or 0),
                total_reviews=0
            ))
        
        # City-wise summary
        city_summary = {}
        for item in performance_items:
            city = item.city
            if city not in city_summary:
                city_summary[city] = {"hostels": 0, "total_beds": 0, "occupied_beds": 0, "total_revenue": 0}
            city_summary[city]["hostels"] += 1
            city_summary[city]["total_beds"] += item.total_beds
            city_summary[city]["occupied_beds"] += item.occupied_beds
            city_summary[city]["total_revenue"] += item.total_revenue
        
        city_wise = [
            {
                "city": city,
                "hostel_count": data["hostels"],
                "total_beds": data["total_beds"],
                "occupancy_rate": (data["occupied_beds"] / data["total_beds"] * 100) if data["total_beds"] > 0 else 0,
                "total_revenue": data["total_revenue"]
            }
            for city, data in city_summary.items()
        ]
        
        summary = {
            "total_hostels": len(performance_items),
            "total_rooms": total_rooms,
            "total_beds": total_beds,
            "total_occupied_beds": total_occupied,
            "overall_occupancy_rate": (total_occupied / total_beds * 100) if total_beds > 0 else 0,
            "total_revenue_all_hostels": float(total_revenue)
        }
        
        return HostelPerformanceResponse(
            summary=summary,
            hostels=performance_items,
            city_wise_summary=city_wise,
            status_wise_summary=[],
            generated_at=datetime.now()
        )
    
    # ==================== OCCUPANCY REPORTS ====================
    
    async def get_occupancy_report(self, filters: ReportFilters) -> OccupancyReportResponse:
        """Generate occupancy report for date range with optimized query for all hostels."""
        
        from datetime import timedelta
        
        # Get hostel IDs - if no filter, get all active hostels
        if filters.hostel_id:
            hostel_ids = [filters.hostel_id]
        else:
            # Get all active hostels
            query = select(Hostel.id).where(
                Hostel.status == HostelStatus.ACTIVE,
                Hostel.is_public == True
            )
            if filters.city:
                query = query.where(Hostel.city.ilike(f"%{filters.city}%"))
            if filters.state:
                query = query.where(Hostel.state.ilike(f"%{filters.state}%"))
            
            result = await self.session.execute(query)
            hostel_ids = [str(row) for row in result.scalars().all()]
            
            # Limit to reasonable number to avoid timeout
            if len(hostel_ids) > 10:
                hostel_ids = hostel_ids[:10]
                print(f"⚠️ Limiting occupancy report to first 10 hostels (from {len(hostel_ids)} total)")
        
        if not hostel_ids:
            return OccupancyReportResponse(
                summary={"message": "No active hostels found for the selected filters"},
                daily_occupancy=[],
                peak_occupancy_date=None,
                peak_occupancy_rate=0.0,
                average_occupancy_rate=0.0,
                generated_at=datetime.now()
            )
        
        # Limit date range to max 31 days to prevent timeout
        date_range = (filters.end_date - filters.start_date).days
        if date_range > 31:
            filters.end_date = filters.start_date + timedelta(days=31)
            print(f"⚠️ Limiting date range to 31 days (was {date_range} days)")
        
        daily_occupancy = []
        total_occupancy_sum = 0
        peak_rate = 0
        peak_date = None
        
        current_date = filters.start_date
        day_count = 0
        
        # Pre-fetch all students to avoid per-hostel queries
        # Get all active students across hostels
        all_students = {}
        student_query = select(Student).where(
            Student.hostel_id.in_(hostel_ids),
            Student.status == StudentStatus.ACTIVE
        )
        student_result = await self.session.execute(student_query)
        students = student_result.scalars().all()
        
        # Group students by hostel
        for student in students:
            hostel_id = str(student.hostel_id)
            if hostel_id not in all_students:
                all_students[hostel_id] = []
            all_students[hostel_id].append(student)
        
        # Pre-fetch bed counts
        bed_counts = {}
        for hostel_id in hostel_ids:
            bed_result = await self.session.execute(
                select(func.count()).select_from(Bed).where(Bed.hostel_id == hostel_id)
            )
            bed_counts[hostel_id] = bed_result.scalar() or 0
        
        # Calculate occupancy day by day
        while current_date <= filters.end_date:
            total_beds = 0
            occupied_beds = 0
            
            for hostel_id in hostel_ids:
                total_beds += bed_counts.get(hostel_id, 0)
                
                # Count occupied beds for this date
                hostel_students = all_students.get(hostel_id, [])
                occupied = sum(1 for s in hostel_students 
                            if s.check_in_date <= current_date 
                            and (s.check_out_date is None or s.check_out_date >= current_date))
                occupied_beds += occupied
            
            occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
            total_occupancy_sum += occupancy_rate
            day_count += 1
            
            if occupancy_rate > peak_rate:
                peak_rate = occupancy_rate
                peak_date = current_date
            
            daily_occupancy.append(OccupancyItem(
                date=current_date,
                total_beds=total_beds,
                occupied_beds=occupied_beds,
                available_beds=total_beds - occupied_beds,
                occupancy_rate=round(occupancy_rate, 1)
            ))
            
            current_date += timedelta(days=1)
        
        avg_occupancy = total_occupancy_sum / day_count if day_count > 0 else 0
        
        summary = {
            "report_period": f"{filters.start_date} to {filters.end_date}",
            "total_beds_available": daily_occupancy[0].total_beds if daily_occupancy else 0,
            "average_occupancy_rate": round(avg_occupancy, 1),
            "peak_occupancy_rate": round(peak_rate, 1),
            "peak_occupancy_date": peak_date.isoformat() if peak_date else None,
            "hostels_included": len(hostel_ids),
            "days_included": day_count
        }
        
        return OccupancyReportResponse(
            summary=summary,
            daily_occupancy=daily_occupancy,
            peak_occupancy_date=peak_date,
            peak_occupancy_rate=round(peak_rate, 1),
            average_occupancy_rate=round(avg_occupancy, 1),
            generated_at=datetime.now()
        )
    
    # ==================== COMPLAINT REPORTS ====================
    
    async def get_complaint_report(self, filters: ReportFilters) -> ComplaintReportResponse:
        """Generate complaint analytics report."""
        
        complaint_query = select(Complaint).where(
            Complaint.created_at >= filters.start_date,
            Complaint.created_at <= filters.end_date
        )
        
        if filters.hostel_id:
            complaint_query = complaint_query.where(Complaint.hostel_id == filters.hostel_id)
        
        result = await self.session.execute(complaint_query)
        complaints = result.scalars().all()
        
        total_complaints = len(complaints)
        
        # By priority
        priority_stats = {}
        for complaint in complaints:
            priority = complaint.priority.lower()
            if priority not in priority_stats:
                priority_stats[priority] = {"total": 0, "resolved": 0}
            priority_stats[priority]["total"] += 1
            if complaint.status in ["resolved", "closed"]:
                priority_stats[priority]["resolved"] += 1
        
        by_priority = []
        for priority, stats in priority_stats.items():
            resolution_rate = (stats["resolved"] / stats["total"] * 100) if stats["total"] > 0 else 0
            by_priority.append(ComplaintSummary(
                priority=priority.title(),
                count=stats["total"],
                resolved_count=stats["resolved"],
                pending_count=stats["total"] - stats["resolved"],
                resolution_rate=round(resolution_rate, 1),
                average_resolution_hours=0
            ))
        
        # By category
        category_stats = {}
        for complaint in complaints:
            cat = complaint.category
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        by_category = [
            {"category": cat, "count": count, "percentage": round(count / total_complaints * 100, 1) if total_complaints > 0 else 0}
            for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # SLA stats (simplified - check if complaint took > 48 hours)
        sla_breached = 0
        for complaint in complaints:
            if complaint.resolved_at and complaint.created_at:
                resolution_hours = (complaint.resolved_at - complaint.created_at).total_seconds() / 3600
                if resolution_hours > 48:
                    sla_breached += 1
            elif complaint.status not in ["resolved", "closed"]:
                # Open complaint older than 48 hours
                if (datetime.now() - complaint.created_at).total_seconds() / 3600 > 48:
                    sla_breached += 1
        
        summary = {
            "report_period": f"{filters.start_date} to {filters.end_date}",
            "total_complaints": total_complaints,
            "resolution_rate": round((sum(s["resolved"] for s in priority_stats.values()) / total_complaints * 100) if total_complaints > 0 else 0, 1),
            "open_complaints": sum(s["total"] - s["resolved"] for s in priority_stats.values())
        }
        
        return ComplaintReportResponse(
            summary=summary,
            by_priority=by_priority,
            by_category=by_category,
            by_hostel=[],
            sla_breached_count=sla_breached,
            sla_compliant_count=total_complaints - sla_breached,
            generated_at=datetime.now()
        )
    
    # ==================== DASHBOARD SUMMARY ====================
    
    async def get_dashboard_summary(self) -> DashboardSummaryResponse:
        """Get super admin dashboard summary with key metrics."""
        
        # Basic counts
        total_hostels = await self.session.execute(select(func.count()).select_from(Hostel))
        active_hostels = await self.session.execute(
            select(func.count()).select_from(Hostel).where(Hostel.status == HostelStatus.ACTIVE)
        )
        pending_hostels = await self.session.execute(
            select(func.count()).select_from(Hostel).where(Hostel.status == HostelStatus.PENDING_APPROVAL)
        )
        
        total_students = await self.session.execute(select(func.count()).select_from(Student))
        active_students = await self.session.execute(
            select(func.count()).select_from(Student).where(Student.status == StudentStatus.ACTIVE)
        )
        
        total_bookings = await self.session.execute(select(func.count()).select_from(Booking))
        pending_bookings = await self.session.execute(
            select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.PENDING_APPROVAL)
        )
        
        # Current month revenue
        today = date.today()
        month_start = date(today.year, today.month, 1)
        month_end = today
        
        revenue_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.status == "captured",
                Payment.created_at >= month_start,
                Payment.created_at <= month_end
            )
        )
        current_month_revenue = float(revenue_result.scalar() or 0)
        
        # Previous month revenue for growth calculation
        if today.month == 1:
            prev_month_start = date(today.year - 1, 12, 1)
            prev_month_end = date(today.year - 1, 12, 31)
        else:
            prev_month_start = date(today.year, today.month - 1, 1)
            prev_month_end = date(today.year, today.month, 1) - timedelta(days=1)
        
        prev_revenue_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.status == "captured",
                Payment.created_at >= prev_month_start,
                Payment.created_at <= prev_month_end
            )
        )
        prev_month_revenue = float(prev_revenue_result.scalar() or 0)
        
        revenue_growth = ((current_month_revenue - prev_month_revenue) / prev_month_revenue * 100) if prev_month_revenue > 0 else 0
        
        # Occupancy rate
        total_beds = await self.session.execute(select(func.count()).select_from(Bed))
        occupied_beds = await self.session.execute(
            select(func.count()).select_from(Student).where(Student.status == StudentStatus.ACTIVE)
        )
        occupancy_rate = (occupied_beds.scalar() or 0) / (total_beds.scalar() or 1) * 100
        
        # Complaint resolution rate
        total_complaints = await self.session.execute(select(func.count()).select_from(Complaint))
        resolved_complaints = await self.session.execute(
            select(func.count()).select_from(Complaint).where(Complaint.status.in_(["resolved", "closed"]))
        )
        resolution_rate = (resolved_complaints.scalar() or 0) / (total_complaints.scalar() or 1) * 100
        
        # Recent activity (last 5 bookings)
        recent_bookings = await self.session.execute(
            select(Booking)
            .order_by(Booking.created_at.desc())
            .limit(5)
        )
        
        recent_activity = []
        for booking in recent_bookings.scalars().all():
            recent_activity.append({
                "type": "booking",
                "id": str(booking.id),
                "status": booking.status.value,
                "created_at": booking.created_at.isoformat(),
                "booking_number": booking.booking_number
            })
        
        return DashboardSummaryResponse(
            total_hostels=total_hostels.scalar() or 0,
            active_hostels=active_hostels.scalar() or 0,
            pending_approval_hostels=pending_hostels.scalar() or 0,
            total_students=total_students.scalar() or 0,
            active_students=active_students.scalar() or 0,
            total_bookings=total_bookings.scalar() or 0,
            pending_bookings=pending_bookings.scalar() or 0,
            total_revenue_month=current_month_revenue,
            revenue_growth_percent=round(revenue_growth, 1),
            occupancy_rate_avg=round(occupancy_rate, 1),
            complaint_resolution_rate=round(resolution_rate, 1),
            recent_activity=recent_activity,
            generated_at=datetime.now()
        )