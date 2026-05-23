# app/api/v1/payments/routes.py
"""
Payment routes for direct tenant-to-admin payments
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import uuid

from app.dependencies import CurrentUser, DBSession, require_roles
from app.schemas.payment import (
    DirectPaymentRequest,
    DirectPaymentResponse,
    QRCodeResponse,
    PaymentStatsResponse,
    PaymentResponse,
    PaymentTypeEnum,
    PaymentMethodEnum,
)
from app.models.payment import Payment
from app.models.student import Student
from app.models.user import User
from app.models.booking import Booking
from app.models.hostel import Hostel
from app.integrations.razorpay import RazorpayClient

router = APIRouter()

# Tenant (student) endpoints
TenantUser = Annotated[CurrentUser, Depends(require_roles("student", "visitor"))]
AdminUser = Annotated[CurrentUser, Depends(require_roles("hostel_admin", "super_admin"))]


# ==================== QR CODE GENERATION ====================

@router.get("/hostels/{hostel_id}/qr-code", response_model=QRCodeResponse)
async def get_hostel_qr_code(
    hostel_id: str,
    amount: Optional[float] = None,
    current_user: AdminUser = None,
    db: DBSession = None,
):
    """
    **Generate QR code for hostel payment (Admin only)**
    
    Returns UPI QR code that tenants can scan to pay.
    """
    # Verify hostel access
    if hostel_id not in current_user.hostel_ids and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied to this hostel")
    
    # Get hostel details
    result = await db.execute(
        select(Hostel).where(Hostel.id == hostel_id)
    )
    hostel = result.scalar_one_or_none()
    
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    
    # Create UPI QR string
    # Format: upi://pay?pa=hostel@upi&pn=HostelName&am=Amount&cu=INR
    upi_id = f"stayease.hostel.{hostel_id[:8]}@okhdfcbank"
    
    qr_string = f"upi://pay?pa={upi_id}&pn={hostel.name.replace(' ', '%20')}&cu=INR"
    if amount and amount > 0:
        qr_string += f"&am={amount}"
    
    # Generate QR code base64 (using qrcode library)
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
    except ImportError:
        # If qrcode not installed, return mock QR
        qr_base64 = f"mock_qr_{hostel_id[:8]}_{amount if amount else 'any'}"
    
    return QRCodeResponse(
        qr_code_base64=qr_base64,
        upi_id=upi_id,
        qr_string=qr_string,
        expires_at=datetime.now() + timedelta(hours=24),
        payment_amount=amount
    )


# ==================== DIRECT PAYMENT (TENANT) ====================

@router.post("/direct-payment", response_model=DirectPaymentResponse, status_code=201)
async def make_direct_payment(
    payload: DirectPaymentRequest,
    background_tasks: BackgroundTasks,
    current_user: TenantUser,
    db: DBSession,
):
    """
    **Make direct payment to hostel admin (Tenant)**
    
    Tenants can pay monthly rent, security deposit, etc.
    Payment is immediately reflected and admin is notified.
    """
    # Get student details
    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found. Please contact hostel admin."
        )
    
    # Verify student is active
    if student.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot make payment. Student status is {student.status}"
        )
    
    # Get booking if provided
    booking = None
    if payload.booking_id:
        result = await db.execute(
            select(Booking).where(Booking.id == payload.booking_id)
        )
        booking = result.scalar_one_or_none()
        
        if booking and str(booking.visitor_id) != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to pay for this booking"
            )
    
    # Generate unique transaction ID
    transaction_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
    
    # Create payment record
    payment = Payment(
        hostel_id=student.hostel_id,
        student_id=student.id,
        booking_id=payload.booking_id,
        amount=float(payload.amount),
        payment_type=payload.payment_type.value,
        payment_method=payload.payment_method.value,
        gateway_order_id=transaction_id,
        gateway_payment_id=transaction_id,
        status="captured",  # Direct payment is considered captured
        receipt_url=None,
        due_date=None,
        paid_at=datetime.now(),
        gateway_signature=None,
    )
    
    # Add description (store in receipt_url temporarily)
    if payload.description:
        payment.receipt_url = payload.description
    
    db.add(payment)
    
    # Update student's advance paid if it's monthly rent
    if payload.payment_type == PaymentTypeEnum.MONTHLY_RENT:
        # Could update student record or booking advance
        if booking:
            booking.booking_advance = float(booking.booking_advance or 0) + float(payload.amount)
    
    await db.commit()
    await db.refresh(payment)
    
    # Send notification to admin (background task)
    background_tasks.add_task(
        notify_admin_payment,
        payment_id=str(payment.id),
        student_id=str(student.id),
        hostel_id=str(student.hostel_id),
        amount=float(payload.amount),
        student_name=current_user.full_name if hasattr(current_user, 'full_name') else "Student"
    )
    
    return DirectPaymentResponse(
        id=str(payment.id),
        student_id=str(student.id),
        hostel_id=str(student.hostel_id),
        amount=float(payment.amount),
        payment_type=payment.payment_type,
        payment_method=payment.payment_method,
        status=payment.status,
        transaction_id=transaction_id,
        description=payload.description,
        created_at=payment.created_at,
        booking_id=payload.booking_id
    )


# ==================== ADMIN PAYMENT ENDPOINTS ====================

@router.get("/admin/hostels/{hostel_id}/payments/recent", response_model=list[PaymentResponse])
async def get_recent_payments(
    hostel_id: str,
    limit: int = 10,
    current_user: AdminUser = None,
    db: DBSession = None,
):
    """Get recent payments for admin dashboard (Admin)"""
    
    if hostel_id not in current_user.hostel_ids and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied to this hostel")
    
    result = await db.execute(
        select(Payment)
        .where(Payment.hostel_id == hostel_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    payments = result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "hostel_id": str(p.hostel_id),
            "student_id": str(p.student_id) if p.student_id else None,
            "booking_id": str(p.booking_id) if p.booking_id else None,
            "amount": float(p.amount),
            "payment_type": p.payment_type,
            "payment_method": p.payment_method,
            "status": p.status,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "paid_at": p.paid_at,
            "gateway_payment_id": p.gateway_payment_id,
        }
        for p in payments
    ]


@router.get("/admin/hostels/{hostel_id}/payments/stats", response_model=PaymentStatsResponse)
async def get_payment_stats(
    hostel_id: str,
    current_user: AdminUser = None,
    db: DBSession = None,
):
    """Get payment statistics for admin dashboard (Admin)"""
    
    if hostel_id not in current_user.hostel_ids and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied to this hostel")
    
    # Get total payments
    total_result = await db.execute(
        select(func.count()).select_from(Payment)
        .where(Payment.hostel_id == hostel_id)
    )
    total_payments = total_result.scalar() or 0
    
    # Get completed amount
    completed_result = await db.execute(
        select(func.sum(Payment.amount))
        .where(
            Payment.hostel_id == hostel_id,
            Payment.status == "captured"
        )
    )
    completed_amount = float(completed_result.scalar() or 0)
    
    # Get recent payments
    recent_result = await db.execute(
        select(Payment)
        .where(Payment.hostel_id == hostel_id, Payment.status == "captured")
        .order_by(Payment.created_at.desc())
        .limit(5)
    )
    recent = recent_result.scalars().all()
    
    return PaymentStatsResponse(
        total_payments=total_payments,
        total_amount=completed_amount,
        pending_amount=0,
        completed_amount=completed_amount,
        recent_payments=[
            {
                "id": str(p.id),
                "hostel_id": str(p.hostel_id),
                "student_id": str(p.student_id) if p.student_id else None,
                "booking_id": str(p.booking_id) if p.booking_id else None,
                "amount": float(p.amount),
                "payment_type": p.payment_type,
                "payment_method": p.payment_method,
                "status": p.status,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in recent
        ]
    )
@router.get("/admin/payments/student/{student_id}", response_model=list[PaymentResponse])
async def get_student_payments_admin(
    student_id: str,
    current_user: Annotated[CurrentUser, Depends(require_roles("hostel_admin", "super_admin"))],
    db: DBSession,
):
    """
    **Get payment history for a specific student (Admin).**
    
    Requires hostel admin or super admin access to the student's hostel.
    """
    from app.models.student import Student
    from sqlalchemy import select
    
    print(f"DEBUG: Admin role: {current_user.role}")
    print(f"DEBUG: Admin hostel_ids: {current_user.hostel_ids}")
    print(f"DEBUG: Looking for student_id: {student_id}")
    
    # Try to get student by ID directly (student_id here is the student record ID, not user ID)
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        # Try as user_id
        result = await db.execute(
            select(Student).where(Student.user_id == student_id)
        )
        student = result.scalar_one_or_none()
    
    if not student:
        print(f"DEBUG: Student not found with ID {student_id}")
        raise HTTPException(status_code=404, detail="Student not found.")
    
    student_hostel_id = str(student.hostel_id)
    print(f"DEBUG: Student belongs to hostel: {student_hostel_id}")
    
    # Check if admin has access to this student's hostel
    if current_user.role != "super_admin":
        # Convert hostel_ids to strings for comparison
        admin_hostel_ids = [str(hid) for hid in current_user.hostel_ids]
        if student_hostel_id not in admin_hostel_ids:
            print(f"DEBUG: Access denied! {student_hostel_id} not in {admin_hostel_ids}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to this student's payment records."
            )
    
    print(f"DEBUG: Access granted!")
    
    # Get payments for this student
    payments_result = await db.execute(
        select(Payment)
        .where(Payment.student_id == student.id)
        .order_by(Payment.created_at.desc())
    )
    payments = payments_result.scalars().all()
    
    print(f"DEBUG: Found {len(payments)} payments for student")
    
    # Convert to response format
    return [
        {
            "id": str(p.id),
            "hostel_id": str(p.hostel_id),
            "student_id": str(p.student_id) if p.student_id else None,
            "booking_id": str(p.booking_id) if p.booking_id else None,
            "amount": float(p.amount),
            "payment_type": p.payment_type,
            "payment_method": p.payment_method,
            "gateway_order_id": p.gateway_order_id,
            "gateway_payment_id": p.gateway_payment_id,
            "gateway_signature": p.gateway_signature,
            "status": p.status,
            "receipt_url": p.receipt_url,
            "due_date": p.due_date,
            "paid_at": p.paid_at,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in payments
    ]

# ==================== STUDENT PAYMENT HISTORY ====================

@router.get("/my-payments", response_model=list[PaymentResponse])
async def get_my_payments(
    current_user: TenantUser,
    db: DBSession,
):
    """Get payment history for logged-in student (Tenant)"""
    
    # Get student ID from user
    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        return []  # Visitor users may not have payments
    
    payments_result = await db.execute(
        select(Payment)
        .where(Payment.student_id == student.id)
        .order_by(Payment.created_at.desc())
    )
    
    payments = payments_result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "hostel_id": str(p.hostel_id),
            "student_id": str(p.student_id) if p.student_id else None,
            "booking_id": str(p.booking_id) if p.booking_id else None,
            "amount": float(p.amount),
            "payment_type": p.payment_type,
            "payment_method": p.payment_method,
            "status": p.status,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "paid_at": p.paid_at,
            "gateway_payment_id": p.gateway_payment_id,
        }
        for p in payments
    ]


@router.get("/my-payments/summary")
async def get_my_payment_summary(
    current_user: TenantUser,
    db: DBSession,
):
    """Get payment summary for logged-in student (Tenant)"""
    
    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        return {
            "total_paid": 0,
            "total_payments": 0,
            "last_payment": None,
            "recent_payments": []
        }
    
    # Calculate totals
    payments_result = await db.execute(
        select(Payment)
        .where(Payment.student_id == student.id, Payment.status == "captured")
        .order_by(Payment.created_at.desc())
    )
    payments = payments_result.scalars().all()
    
    total_paid = sum(float(p.amount) for p in payments)
    total_payments = len(payments)
    last_payment = payments[0] if payments else None
    
    return {
        "total_paid": total_paid,
        "total_payments": total_payments,
        "last_payment_date": last_payment.created_at.isoformat() if last_payment else None,
        "last_payment_amount": float(last_payment.amount) if last_payment else 0,
        "recent_payments": [
            {
                "amount": float(p.amount),
                "payment_type": p.payment_type,
                "created_at": p.created_at.isoformat(),
                "transaction_id": p.gateway_payment_id
            }
            for p in payments[:5]
        ]
    }


# ==================== NOTIFICATION FUNCTION ====================

async def notify_admin_payment(
    payment_id: str,
    student_id: str,
    hostel_id: str,
    amount: float,
    student_name: str
):
    """Send notification to admin about new payment"""
    # This can be implemented with WebSocket, email, or push notification
    try:
        from app.integrations.email import EmailService
        
        # Get admin email for this hostel
        from app.models.hostel import AdminHostelMapping
        from app.models.user import User
        from sqlalchemy import select
        
        # Use the provided session or create a new one
        # For background task, we need a new session
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get admin email
            result = await session.execute(
                select(User.email, User.full_name)
                .join(AdminHostelMapping, AdminHostelMapping.admin_id == User.id)
                .where(AdminHostelMapping.hostel_id == hostel_id)
                .limit(1)
            )
            admin = result.first()
            
            if admin:
                email_service = EmailService()
                await email_service.send_email(
                    to=admin.email,
                    subject=f"💰 New Payment Received - ₹{amount:,.2f}",
                    html=f"""
                    <h2>New Payment Received</h2>
                    <p>Student: <strong>{student_name}</strong></p>
                    <p>Amount: <strong>₹{amount:,.2f}</strong></p>
                    <p>Payment ID: {payment_id}</p>
                    <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Log in to the admin dashboard to view details.</p>
                    """
                )
    except Exception as e:
        print(f"Failed to send admin notification: {e}")