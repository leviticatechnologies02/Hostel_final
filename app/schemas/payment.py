from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from app.schemas.base import APIModel
from typing import Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum



class BookingPaymentCreateRequest(BaseModel):
    booking_advance: float = Field(ge=0)
    payment_method: str = Field(default="razorpay", min_length=2, max_length=50)


class BookingPaymentOrderResponse(BaseModel):
    payment: "PaymentResponse"
    razorpay_order: dict


class RazorpayWebhookRequest(BaseModel):
    event: str
    payload: dict


class PaymentResponse(APIModel):
    id: str
    hostel_id: str
    student_id: str | None = None
    booking_id: str | None = None
    amount: float
    payment_type: str
    payment_method: str
    gateway_order_id: str | None = None
    gateway_payment_id: str | None = None
    gateway_signature: str | None = None
    status: str
    receipt_url: str | None = None
    due_date: date | None = None
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    remaining_balance: float | None = None
    
class PaymentTypeEnum(str, Enum):
    BOOKING_ADVANCE = "booking_advance"
    MONTHLY_RENT = "monthly_rent"
    SECURITY_DEPOSIT = "security_deposit"
    MAINTENANCE_FEE = "maintenance_fee"
    OTHER = "other"
    
class PaymentMethodEnum(str, Enum):
    RAZORPAY = "razorpay"
    QR_SCAN = "qr_scan"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"


class DirectPaymentRequest(BaseModel):
    """Request for direct tenant-to-admin payment"""
    student_id: str = Field(..., description="Student making the payment")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Payment amount")
    payment_type: PaymentTypeEnum = Field(default=PaymentTypeEnum.MONTHLY_RENT)
    description: Optional[str] = Field(None, max_length=500)
    payment_method: PaymentMethodEnum = Field(default=PaymentMethodEnum.QR_SCAN)
    booking_id: Optional[str] = Field(None, description="Optional booking reference")

class DirectPaymentResponse(BaseModel):
    """Response after direct payment"""
    id: str
    student_id: str
    hostel_id: str
    amount: float
    payment_type: str
    payment_method: str
    status: str
    transaction_id: str
    description: Optional[str] = None
    created_at: datetime
    booking_id: Optional[str] = None


class QRCodeResponse(BaseModel):
    """Response with QR code details"""
    qr_code_base64: str
    upi_id: str
    qr_string: str
    expires_at: datetime
    payment_amount: Optional[float] = None


class PaymentStatsResponse(BaseModel):
    """Payment statistics for dashboard"""
    total_payments: int
    total_amount: float
    pending_amount: float
    completed_amount: float
    recent_payments: list["PaymentResponse"]


class PaymentWebhookPayload(BaseModel):
    """Webhook payload for payment notifications"""
    payment_id: str
    student_id: str
    hostel_id: str
    amount: float
    status: str
    transaction_id: str
    timestamp: datetime