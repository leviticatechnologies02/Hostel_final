"""
Background payment tasks using Celery.
"""
from app.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def process_payment_webhook_task(self, event_data: dict):
    """Process Razorpay payment webhook as background task."""
    try:
        from app.services.payment_service import PaymentService
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            PaymentService(db).process_webhook_event(event_data)
        finally:
            db.close()
            
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(bind=True, max_retries=3)
def send_payment_reminder_task(
    self,
    student_email: str,
    student_name: str,
    payment_due_amount: float,
    due_date: str
):
    """Send payment reminder email as background task."""
    try:
        from app.integrations.email import EmailService
        
        email_service = EmailService()
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Simple text email for now
        html_content = f"""
        <html>
        <body>
            <h2>Payment Reminder</h2>
            <p>Dear {student_name},</p>
            <p>This is a reminder that your payment of ₹{payment_due_amount:,.2f} is due on {due_date}.</p>
            <p>Please log in to your account to complete the payment.</p>
            <p>Best regards,<br>Levitica Nestora Team</p>
        </body>
        </html>
        """
        
        from fastapi_mail import MessageSchema, MessageType
        from pydantic import EmailStr
        
        message = MessageSchema(
            subject=f"Payment Reminder - ₹{payment_due_amount:,.2f}",
            recipients=[student_email],
            body=html_content,
            subtype=MessageType.html
        )
        
        import asyncio
        loop.run_until_complete(email_service.fastmail.send_message(message))
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)
