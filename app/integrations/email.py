"""
Email service for StayEase.
Uses aiosmtplib for async SMTP — works with Gmail, Mailtrap, and any SMTP provider.
Falls back to console logging when SMTP is not configured (dev mode).
"""
import logging
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    s = get_settings()
    if s.email_provider.lower() == "brevo":
        return bool(s.brevo_api_key)

    placeholders = {
        "", "your-mailtrap-username", "your-email@gmail.com",
        "your-gmail@gmail.com", "your-mailtrap-password",
        "your-app-password", "your-16-char-app-password",
    }
    return bool(
        s.smtp_user and s.smtp_user not in placeholders
        and s.smtp_password and s.smtp_password not in placeholders
    )


async def _send_smtp(*, to: str, subject: str, html: str) -> None:
    """Send email via aiosmtplib. Raises on failure."""
    import aiosmtplib

    s = get_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"StayEase <{s.email_from}>"
    msg["To"] = to
    
    # Strip basic HTML tags for the plain text version
    import re
    text = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    use_tls = s.smtp_port == 465
    use_starttls = s.smtp_port in (587, 2525)

    await aiosmtplib.send(
        msg,
        hostname=s.smtp_host,
        port=s.smtp_port,
        username=s.smtp_user,
        password=s.smtp_password,
        use_tls=use_tls,
        start_tls=use_starttls,
        timeout=10,
    )


async def _send_brevo(*, to: str, subject: str, html: str) -> None:
    """Send email via Brevo REST API. Raises on failure."""
    import httpx

    s = get_settings()
    sender_email = s.brevo_sender_email or s.email_from
    
    headers = {
        "accept": "application/json",
        "api-key": s.brevo_api_key,
        "content-type": "application/json",
    }
    
    import re
    text_content = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
    text_content = re.sub(r'<[^>]+>', ' ', text_content)
    text_content = re.sub(r'\s+', ' ', text_content).strip()

    payload = {
        "sender": {
            "name": "StayEase",
            "email": sender_email
        },
        "to": [
            {
                "email": to
            }
        ],
        "subject": subject,
        "htmlContent": html,
        "textContent": text_content
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers=headers,
            json=payload,
            timeout=s.email_send_timeout
        )
        if response.status_code >= 400:
            logger.error(f"[EMAIL] Brevo API error {response.status_code}: {response.text}")
            raise Exception(f"Brevo API error: {response.text}")


async def send_email(*, to: str, subject: str, html: str) -> bool:
    """
    Send an HTML email. Returns True on success, False on failure.
    Always logs to console (useful for dev/test).
    """
    logger.info(f"[EMAIL] To: {to} | Subject: {subject}")
    s = get_settings()

    if not _is_configured():
        logger.info("[EMAIL] Email provider not fully configured — email logged only (dev mode)")
        logger.info(f"[EMAIL] Dev mode raw HTML sample: {html[:200]}...")
        return True

    try:
        if s.email_provider.lower() == "brevo":
            await _send_brevo(to=to, subject=subject, html=html)
        else:
            await _send_smtp(to=to, subject=subject, html=html)
        logger.info(f"[EMAIL] Sent successfully to {to}")
        return True
    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send to {to}: {exc}")
        return False


# ── HTML Templates ────────────────────────────────────────────────────────────

def _base(title: str, header_color: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f4f4f4;color:#333}}
  .wrap{{max-width:600px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
  .hdr{{background:{header_color};padding:32px 24px;text-align:center;color:#fff}}
  .hdr h1{{font-size:24px;font-weight:700}}
  .hdr p{{margin-top:6px;opacity:.85;font-size:14px}}
  .body{{padding:32px 24px}}
  .row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f0f0f0}}
  .row:last-child{{border-bottom:none}}
  .lbl{{color:#888;font-size:13px}}
  .val{{font-weight:600;font-size:13px}}
  .otp{{font-size:48px;font-weight:800;letter-spacing:8px;color:{header_color};text-align:center;padding:24px;background:#f9f9f9;border-radius:8px;margin:20px 0}}
  .btn{{display:inline-block;padding:14px 28px;background:{header_color};color:#fff;text-decoration:none;border-radius:8px;font-weight:600;margin-top:20px}}
  .warn{{background:#fffbeb;border-left:4px solid #f59e0b;padding:14px;border-radius:4px;margin:16px 0;font-size:13px}}
  .ftr{{background:#f9f9f9;padding:20px 24px;text-align:center;font-size:12px;color:#aaa}}
</style>
</head>
<body>
<div class="wrap">
{body}
<div class="ftr">© 2026 StayEase · support@stayease.com · <a href="http://localhost:5173" style="color:#FF6B35">stayease.com</a></div>
</div>
</body>
</html>"""


def otp_email_html(name: str, otp: str, purpose: str = "verification") -> str:
    body = f"""
<div class="hdr" style="background:#FF6B35">
  <h1>🔐 {'Email Verification' if purpose == 'registration' else 'Password Reset'}</h1>
  <p>Your one-time password</p>
</div>
<div class="body">
  <p>Hi <strong>{name}</strong>,</p>
  <p style="margin-top:12px">{'Use this OTP to verify your email and activate your StayEase account.' if purpose == 'registration' else 'Use this OTP to reset your StayEase password.'}</p>
  <div class="otp">{otp}</div>
  <div class="warn">
    ⏱ This OTP expires in <strong>10 minutes</strong>.<br>
    🔒 Never share this code with anyone.<br>
    {'If you did not register, ignore this email.' if purpose == 'registration' else 'If you did not request a reset, ignore this email.'}
  </div>
</div>"""
    return _base("OTP — StayEase", "#FF6B35", body)


def booking_confirmation_html(
    name: str,
    booking_number: str,
    hostel_name: str,
    check_in: str,
    check_out: str,
    amount: float,
    status: str,
) -> str:
    body = f"""
<div class="hdr" style="background:#2D6A4F">
  <h1>🏠 Booking Confirmed!</h1>
  <p>Your stay at {hostel_name} is booked</p>
</div>
<div class="body">
  <p>Hi <strong>{name}</strong>, your booking is confirmed.</p>
  <div style="margin:20px 0;background:#f9f9f9;border-radius:8px;padding:20px">
    <div class="row"><span class="lbl">Booking #</span><span class="val">{booking_number}</span></div>
    <div class="row"><span class="lbl">Hostel</span><span class="val">{hostel_name}</span></div>
    <div class="row"><span class="lbl">Check-in</span><span class="val">{check_in}</span></div>
    <div class="row"><span class="lbl">Check-out</span><span class="val">{check_out}</span></div>
    <div class="row"><span class="lbl">Amount Paid</span><span class="val">₹{amount:,.0f}</span></div>
    <div class="row"><span class="lbl">Status</span><span class="val" style="color:#2D6A4F">{status.upper()}</span></div>
  </div>
  <p>Arrive on your check-in date with this booking number. The hostel admin will check you in.</p>
  <div style="text-align:center"><a href="http://localhost:5173/my-bookings" class="btn" style="background:#2D6A4F">View My Bookings</a></div>
</div>"""
    return _base("Booking Confirmed — StayEase", "#2D6A4F", body)


def payment_receipt_html(
    name: str,
    amount: float,
    payment_type: str,
    transaction_id: str,
    payment_date: str,
) -> str:
    body = f"""
<div class="hdr" style="background:#06D6A0">
  <h1>✅ Payment Successful</h1>
  <p>₹{amount:,.0f} received</p>
</div>
<div class="body">
  <p>Hi <strong>{name}</strong>, your payment was processed successfully.</p>
  <div style="margin:20px 0;background:#f9f9f9;border-radius:8px;padding:20px">
    <div class="row"><span class="lbl">Amount</span><span class="val" style="color:#06D6A0;font-size:20px">₹{amount:,.0f}</span></div>
    <div class="row"><span class="lbl">Type</span><span class="val">{payment_type.replace('_',' ').title()}</span></div>
    <div class="row"><span class="lbl">Transaction ID</span><span class="val">{transaction_id}</span></div>
    <div class="row"><span class="lbl">Date</span><span class="val">{payment_date}</span></div>
  </div>
  <p>Keep this email as your payment receipt.</p>
</div>"""
    return _base("Payment Receipt — StayEase", "#06D6A0", body)


def welcome_email_html(name: str) -> str:
    body = f"""
<div class="hdr" style="background:linear-gradient(135deg,#FF6B35,#FFD166)">
  <h1>🎉 Welcome to StayEase!</h1>
  <p>India's trusted hostel booking platform</p>
</div>
<div class="body">
  <p>Hi <strong>{name}</strong>, welcome aboard!</p>
  <p style="margin-top:12px">You can now browse verified hostels, book by day or month, and manage everything from your dashboard.</p>
  <div style="margin:24px 0;display:grid;gap:12px">
    {''.join(f'<div style="display:flex;align-items:center;gap:12px;padding:12px;background:#f9f9f9;border-radius:8px"><span style="font-size:24px">{icon}</span><div><strong>{title}</strong><br><span style="font-size:13px;color:#888">{desc}</span></div></div>' for icon, title, desc in [
        ('🏠','Browse Hostels','Verified properties across India'),
        ('📅','Flexible Booking','Daily or monthly — your choice'),
        ('💳','Secure Payments','Razorpay-powered safe transactions'),
        ('📱','Track Everything','Bookings, payments, complaints in one place'),
    ])}
  </div>
  <div style="text-align:center"><a href="http://localhost:5173/hostels" class="btn">Explore Hostels</a></div>
  <p>Your journey to hassle-free hostel living starts now!</p>
</div>"""
    return _base("Welcome to StayEase!", "#FF6B35", body)


def contact_lead_html(
    full_name: str,
    hostel_name: str,
    city: str,
    inquiry_type: str,
    message: str,
) -> str:
    """Delegate to the premium contact lead confirmation template."""
    from app.integrations.email_templates_premium import contact_lead_html_v2
    return contact_lead_html_v2(
        full_name=full_name,
        hostel_name=hostel_name,
        city=city,
        inquiry_type=inquiry_type,
        message=message,
    )


# ── High-level helpers used by services ──────────────────────────────────────

class EmailService:
    """Thin wrapper kept for backward compatibility with existing service calls."""

    async def send_password_reset_otp(self, *, recipient_email: str, recipient_name: str, otp: str) -> bool:
        return await send_email(
            to=recipient_email,
            subject="Password Reset OTP — StayEase",
            html=otp_email_html(recipient_name, otp, "password_reset"),
        )

    async def send_registration_otp(self, *, recipient_email: str, recipient_name: str, otp: str) -> bool:
        return await send_email(
            to=recipient_email,
            subject="Verify Your Email — StayEase",
            html=otp_email_html(recipient_name, otp, "registration"),
        )

    async def send_booking_confirmation(
        self, *, recipient_email: str, recipient_name: str,
        booking_number: str, hostel_name: str,
        check_in_date: str, check_out_date: str,
        total_amount: float, payment_status: str,
    ) -> bool:
        return await send_email(
            to=recipient_email,
            subject=f"Booking Confirmed {booking_number} — StayEase",
            html=booking_confirmation_html(
                recipient_name, booking_number, hostel_name,
                check_in_date, check_out_date, total_amount, payment_status,
            ),
        )

    async def send_payment_receipt(
        self, *, recipient_email: str, recipient_name: str,
        payment_id: str, amount: float, payment_type: str,
        transaction_id: str, payment_date: str,
    ) -> bool:
        return await send_email(
            to=recipient_email,
            subject=f"Payment Receipt ₹{amount:,.0f} — StayEase",
            html=payment_receipt_html(recipient_name, amount, payment_type, transaction_id, payment_date),
        )

    async def send_registration_welcome(self, *, recipient_email: str, recipient_name: str) -> bool:
        return await send_email(
            to=recipient_email,
            subject="Welcome to StayEase! 🎉",
            html=welcome_email_html(recipient_name),
        )

    async def send_contact_lead_confirmation(
        self, *, recipient_email: str, recipient_name: str,
        hostel_name: str, city: str, inquiry_type: str, message: str
    ) -> bool:
        return await send_email(
            to=recipient_email,
            subject="We received your inquiry — StayEase",
            html=contact_lead_html(recipient_name, hostel_name, city, inquiry_type, message),
        )

    async def send_owner_contact_notification(
        self, *, owner_email: str, first_name: str, last_name: str,
        organization_name: str, email: str, phone: str, message: str, submitted_at: str
    ) -> bool:
        subject = f"\U0001f3e8 New Contact Inquiry Received | {organization_name} | {first_name} {last_name}"
        return await send_email(
            to=owner_email,
            subject=subject,
            html=_owner_notification_html(
                first_name=first_name,
                last_name=last_name,
                organization_name=organization_name,
                email=email,
                phone=phone,
                message=message,
                submitted_at=submitted_at,
            ),
        )


def _owner_notification_html(
    first_name: str,
    last_name: str,
    organization_name: str,
    email: str,
    phone: str,
    message: str,
    submitted_at: str,
) -> str:
    """Delegate to the premium owner notification template."""
    from app.integrations.email_templates_premium import owner_notification_html_v2
    return owner_notification_html_v2(
        first_name=first_name,
        last_name=last_name,
        organization_name=organization_name,
        email=email,
        phone=phone,
        message=message,
        submitted_at=submitted_at,
    )
