from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi import Request, status
from pydantic import ValidationError as PydanticValidationError

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.middleware import register_middleware

settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# Swagger / OpenAPI description — rendered at http://localhost:8000/docs
# ─────────────────────────────────────────────────────────────────────────────
_DESCRIPTION = """
# 🏠 StayEase API — Multi-Tenant Hostel Management & Booking Platform

> **India's hostel management platform** — bed-level inventory, day-wise & monthly bookings,
> multi-role operations, Razorpay payments, and Gmail OTP emails.
> Built for **Levitica Technologies — DCM StayEase**.

---

## 🔑 Quick Start — Test Credentials

All accounts use password: **`Test@1234`**

| Role | Email | Access |
|------|-------|--------|
| 🛡️ Super Admin | `superadmin@stayease.com` | Full platform control |
| 🏢 Hostel Admin 1 | `admin1@stayease.com` | Hyderabad + Bangalore hostels |
| 🏢 Hostel Admin 2 | `admin2@stayease.com` | Pune + Mumbai hostels |
| 👷 Supervisor 1 | `supervisor1@stayease.com` | Green Valley Boys Hostel |
| 👷 Supervisor 2 | `supervisor2@stayease.com` | Pearl Girls Hostel |
| 🧑‍🎓 Student (Hemant) | `hemant.pawade.lev044@levitica.in` | Student self-service |
| 🙋 Visitor | `arun.kapoor@gmail.com` | Public booking flow |

> 63 student accounts from Levitica employee register — pattern: `firstname.lastname.LEVXXX@levitica.in`

**How to authenticate:**
1. Call `POST /api/v1/auth/login` with email + password
2. Copy the `access_token` from the response
3. Click **Authorize 🔒** (top right) → paste `Bearer <token>`

---

## 🗺️ API Sections (126 routes)

### 🌐 `public` — No auth required
Browse hostels, view rooms, read reviews, submit inquiries, search autocomplete, compare hostels.

### 🔐 `auth` — Authentication flows
Register visitor → verify OTP (email sent via Gmail) → login → refresh token → logout → forgot/reset password.

### 👑 `super-admin` — Platform management
Approve/reject/suspend hostels, create hostel admins, assign hostels, manage subscriptions, add hostel images.

### 🏢 `admin` — Hostel operations
Manage rooms & beds, approve/reject bookings, check-in/check-out students,
handle complaints (SLA tracking), attendance analytics, maintenance, notices, mess menu, supervisors.

### 👷 `supervisor` — Day-to-day workflows
Bulk attendance marking, complaint handling, maintenance requests, notices, mess menu view.

### 🧑‍🎓 `student` — Self-service portal
Profile (edit + room info + leave request), bookings with timeline, payments, attendance calendar,
complaints with photo upload, notices (read tracking), mess menu, waitlist.

### 🙋 `visitor` — Visitor portal
Profile, booking history, reviews, saved favorites.

### 🔔 `webhooks` — Razorpay payment events
HMAC-SHA256 signature verification, idempotent payment capture, booking confirmation email.

---

## 🔄 Booking Lifecycle

```
Visitor creates booking
        │
        ▼
  DRAFT ──── 30 min expiry (Celery) ────▶ CANCELLED
        │
        ▼
  PAYMENT_PENDING ──── Razorpay payment ────▶ PENDING_APPROVAL
                                                      │
                                           Admin reviews booking
                                                      │
                              ┌───────────────────────┴───────────────────────┐
                              ▼                                               ▼
                          APPROVED                                        REJECTED
                              │                                       (bed released)
                    Admin assigns bed
                    BedStay = RESERVED
                              │
                         CHECK-IN
                    BedStay = ACTIVE
                    Student record created
                              │
                        CHECK-OUT
                    BedStay = COMPLETED
                              │
                         COMPLETED

Any status → CANCELLED (bed released if assigned)
```

---

## 🛏️ Bed Availability Rules

- **BedStay** is the source of truth — NOT the booking table
- Overlap check: `start_date < end_date2 AND end_date > start_date2`
- Bed assigned only on **APPROVED** — never at booking creation
- Cancel/Reject → BedStay `CANCELLED` → bed freed immediately

---

## 🏢 Multi-Tenancy

- `hostel_admin` → only assigned hostel(s) data
- `supervisor` → only assigned hostel
- `student` → only own records
- `super_admin` → bypasses all tenancy checks

---

## 💳 Payment Flow

```
1. POST /bookings/{id}/payment → Razorpay order created
2. Frontend opens Razorpay checkout
3. On success → Razorpay calls POST /webhooks/razorpay
4. Webhook verifies HMAC-SHA256 signature
5. Idempotency check (event already processed?)
6. Booking → PENDING_APPROVAL
7. Booking confirmation email sent to visitor
8. Admin reviews and approves/rejects
```

---

## 📧 Email Notifications

- OTP verification on registration
- Password reset OTP
- Booking confirmation on payment capture
- All sent via Gmail SMTP (configured in `.env`)
- Dev mode: OTPs printed to console if SMTP not configured

---

## 📊 Seed Data (63 Levitica Employees)

Students are seeded from `Employee_Register.xlsx`:
- 63 employees (LEV001–LEV128) as students
- Student numbers: `LEV044-22` format (code + row index)
- Emails: `hemant.pawade.lev044@levitica.in`
- Team leads mapped to supervisors

*Base URL: `http://localhost:8000/api/v1` · Docs: `/docs` · ReDoc: `/redoc`*
"""



# ─────────────────────────────────────────────────────────────────────────────
# Tag metadata — controls section order and descriptions in Swagger UI
# ─────────────────────────────────────────────────────────────────────────────
_TAGS_METADATA = [
    {
        "name": "public",
        "description": "🌐 **Public endpoints** — no authentication required. "
                       "Browse hostels, view rooms & reviews, submit inquiries, create bookings.",
    },
    {
        "name": "auth",
        "description": "🔐 **Authentication** — register, OTP verify, login, token refresh, "
                       "logout, forgot/reset password.",
    },
    {
        "name": "super-admin",
        "description": "👑 **Super Admin** — platform-wide management. "
                       "Approve hostels, create admins, assign hostels, manage subscriptions.",
    },
    {
        "name": "admin",
        "description": "🏢 **Hostel Admin** — full hostel operations. "
                       "Rooms, beds, bookings, students, payments, complaints, attendance, "
                       "maintenance, notices, mess menu, supervisors.",
    },
    {
        "name": "supervisor",
        "description": "👷 **Supervisor** — day-to-day hostel workflows. "
                       "Attendance marking, complaint handling, maintenance requests, notices, mess menu.",
    },
    {
        "name": "student",
        "description": "🧑‍🎓 **Student** — self-service portal. "
                       "Profile, bookings, payments, attendance, complaints, notices, mess menu.",
    },
    {
        "name": "webhooks",
        "description": "🔔 **Webhooks** — Razorpay payment event processing. "
                       "Signature-verified and idempotent.",
    },
    {
        "name": "health",
        "description": "💚 **Health check** — server liveness probe.",
    },
    {
        "name": "reports",
        "description": "📊 **Super Admin Reports** — comprehensive analytics and reporting. "
                       "Financial reports, booking analytics, occupancy tracking, "
                       "hostel performance metrics, and complaint analysis with "
                       "CSV/JSON export capabilities.",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="StayEase API",
    version="1.0.0",
    description=_DESCRIPTION,
    openapi_tags=_TAGS_METADATA,
    contact={
        "name": "StayEase Platform",
        "email": "support@stayease.com",
    },
    license_info={
        "name": "MIT",
    },
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,       # collapse schemas by default — cleaner view
        "docExpansion": "none",               # all sections collapsed on load
        "filter": True,                       # enable search/filter bar
        "tryItOutEnabled": True,              # "Try it out" enabled by default
        "persistAuthorization": True,         # keep auth token across page reloads
        "displayRequestDuration": True,       # show response time on each request
        "syntaxHighlight.theme": "monokai",   # dark code highlighting
    },
)

register_middleware(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
async def root():
    """Animated StayEase API landing page."""
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>StayEase API</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f1a;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden}
  .bg{position:fixed;inset:0;z-index:0}
  .blob{position:absolute;border-radius:50%;filter:blur(80px);opacity:.25;animation:float 8s ease-in-out infinite}
  .blob1{width:500px;height:500px;background:#FF6B35;top:-10%;left:-10%;animation-delay:0s}
  .blob2{width:400px;height:400px;background:#4361ee;bottom:-10%;right:-10%;animation-delay:3s}
  .blob3{width:300px;height:300px;background:#06D6A0;top:40%;left:50%;animation-delay:5s}
  @keyframes float{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-30px) scale(1.05)}}
  .card{position:relative;z-index:1;background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);border-radius:24px;padding:48px 56px;max-width:680px;width:90%;text-align:center;animation:slideUp .8s ease both}
  @keyframes slideUp{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:translateY(0)}}
  .logo{display:inline-flex;align-items:center;gap:12px;margin-bottom:32px}
  .logo-icon{width:52px;height:52px;background:#FF6B35;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:24px;box-shadow:0 8px 32px rgba(255,107,53,.4);animation:pulse 2s ease-in-out infinite}
  @keyframes pulse{0%,100%{box-shadow:0 8px 32px rgba(255,107,53,.4)}50%{box-shadow:0 8px 48px rgba(255,107,53,.7)}}
  .logo-text{font-size:28px;font-weight:800;letter-spacing:-0.5px}
  .logo-text span{color:#FF6B35}
  h1{font-size:36px;font-weight:800;line-height:1.2;margin-bottom:12px;background:linear-gradient(135deg,#fff 0%,#aaa 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
  .subtitle{color:rgba(255,255,255,.5);font-size:16px;margin-bottom:40px;line-height:1.6}
  .status{display:inline-flex;align-items:center;gap:8px;background:rgba(6,214,160,.1);border:1px solid rgba(6,214,160,.3);color:#06D6A0;padding:8px 18px;border-radius:100px;font-size:13px;font-weight:600;margin-bottom:40px}
  .dot{width:8px;height:8px;background:#06D6A0;border-radius:50%;animation:blink 1.5s ease-in-out infinite}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
  .links{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:40px}
  .link-card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:18px;text-decoration:none;color:#fff;transition:all .2s;display:flex;flex-direction:column;gap:6px;text-align:left}
  .link-card:hover{background:rgba(255,107,53,.1);border-color:rgba(255,107,53,.4);transform:translateY(-2px)}
  .link-card .icon{font-size:22px;margin-bottom:4px}
  .link-card .title{font-weight:700;font-size:15px}
  .link-card .desc{font-size:12px;color:rgba(255,255,255,.4)}
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;border-top:1px solid rgba(255,255,255,.08);padding-top:32px}
  .stat{text-align:center}
  .stat-val{font-size:22px;font-weight:800;color:#FF6B35}
  .stat-label{font-size:11px;color:rgba(255,255,255,.4);margin-top:4px;text-transform:uppercase;letter-spacing:.5px}
  .version{margin-top:24px;font-size:12px;color:rgba(255,255,255,.25)}
</style>
</head>
<body>
<div class="bg">
  <div class="blob blob1"></div>
  <div class="blob blob2"></div>
  <div class="blob blob3"></div>
</div>
<div class="card">
  <div class="logo">
    <div class="logo-icon">🏠</div>
    <div class="logo-text">Stay<span>Ease</span></div>
  </div>
  <h1>Hostel Management API</h1>
  <p class="subtitle">India's hostel booking platform — bed-level inventory,<br>multi-role operations &amp; Razorpay-integrated payments.</p>
  <div class="status"><span class="dot"></span> API is live and running</div>
  <div class="links">
    <a class="link-card" href="/docs">
      <div class="icon">📖</div>
      <div class="title">Swagger UI</div>
      <div class="desc">Interactive API explorer with try-it-out</div>
    </a>
    <a class="link-card" href="/redoc">
      <div class="icon">📚</div>
      <div class="title">ReDoc</div>
      <div class="desc">Clean reference documentation</div>
    </a>
    <a class="link-card" href="/api/v1/public/hostels">
      <div class="icon">🏨</div>
      <div class="title">Public Hostels</div>
      <div class="desc">Browse live hostel listings</div>
    </a>
    <a class="link-card" href="/health">
      <div class="icon">💚</div>
      <div class="title">Health Check</div>
      <div class="desc">Server liveness probe</div>
    </a>
  </div>
  <div class="stats">
    <div class="stat"><div class="stat-val">9</div><div class="stat-label">API Modules</div></div>
    <div class="stat"><div class="stat-val">60+</div><div class="stat-label">Endpoints</div></div>
    <div class="stat"><div class="stat-val">5</div><div class="stat-label">User Roles</div></div>
  </div>
  <div class="version">StayEase API v1.0.0 &nbsp;·&nbsp; FastAPI &nbsp;·&nbsp; PostgreSQL &nbsp;·&nbsp; Redis</div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/health", tags=["health"])
async def healthcheck():
    """Server liveness probe — returns 200 if the API is running."""
    return {"status": "ok", "version": "1.0.0", "platform": "StayEase"}


_HTTP_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "unprocessable_entity",
    429: "too_many_requests",
    500: "internal_error",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    code = _HTTP_CODE_MAP.get(exc.status_code, "error")
    detail = exc.detail
    if not isinstance(detail, str):
        detail = str(detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail, "code": code})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors and return 422."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "code": "validation_error",
            "errors": errors
        }
    )

# In app/main.py, update the pydantic validation exception handler:

@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
    """Convert Pydantic validation errors to 400 Bad Request."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    # Always return 400 for validation errors from our API
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Validation error",
            "code": "validation_error",
            "errors": errors
        }
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Not found.", "code": "not_found"})


@app.exception_handler(500)
async def server_error_handler(request, exc):
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error.", "code": "internal_error"}
    )
