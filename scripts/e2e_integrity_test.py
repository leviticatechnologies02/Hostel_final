"""
End-to-end integrity test — verifies all data integrity rules are enforced.
Run: python scripts/e2e_integrity_test.py
"""
import asyncio
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000/api/v1"
PASS = "[PASS]"
FAIL = "[FAIL]"


def req(method, path, body=None, headers=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {}
        except Exception:
            return e.code, {"detail": raw.decode("utf-8", errors="replace")}


def check(label, condition, detail=""):
    icon = PASS if condition else FAIL
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""))
    return condition


print("\n" + "=" * 60)
print("  StayEase — Integrity & Relationship Test Suite")
print("=" * 60)

# ── 1. Auth ───────────────────────────────────────────────────────────
print("\n[1] Auth")
status, data = req("POST", "/auth/login", {"email_or_phone": "superadmin@stayease.com", "password": "Test@1234"})
check("Super admin login", status == 200, f"status={status}")
sa_token = data.get("access_token", "")

status, data = req("POST", "/auth/login", {"email_or_phone": "admin1@stayease.com", "password": "Test@1234"})
check("Admin login", status == 200, f"status={status}")
admin_token = data.get("access_token", "")
admin_hostel_ids = data.get("hostel_ids", [])

status, data = req("POST", "/auth/login", {"email_or_phone": "arun.kapoor@gmail.com", "password": "Test@1234"})
check("Visitor login", status == 200, f"status={status}")
visitor_token = data.get("access_token", "")
visitor_id = data.get("user_id", "")

status, data = req("POST", "/auth/login", {"email_or_phone": "rahul.sharma@student.com", "password": "Test@1234"})
check("Student login", status == 200, f"status={status}")
student_token = data.get("access_token", "")

# ── 2. Public endpoints ───────────────────────────────────────────────
print("\n[2] Public")
status, data = req("GET", "/public/hostels")
check("List hostels", status == 200 and len(data) > 0, f"{len(data)} hostels")

status, data = req("GET", "/public/hostels/green-valley-boys-hostel")
check("Hostel detail by slug", status == 200, data.get("name", ""))
hostel_id = data.get("id", "")

status, data = req("GET", f"/public/hostels/{hostel_id}/rooms")
check("Hostel rooms", status == 200 and len(data) > 0, f"{len(data)} rooms")
room_id = data[0]["id"] if data else ""

status, data = req("GET", f"/public/hostels/{hostel_id}/reviews")
check("Hostel reviews", status == 200, f"{len(data)} reviews")

status, data = req("GET", "/public/cities")
check("Cities list", status == 200 and len(data) > 0, str(data))

# ── 3. Booking integrity ──────────────────────────────────────────────
print("\n[3] Booking Integrity")

# Invalid dates (check_out <= check_in) must be rejected
status, data = req("POST", "/public/bookings", {
    "hostel_id": hostel_id, "room_id": room_id,
    "booking_mode": "daily",
    "check_in_date": "2026-06-10", "check_out_date": "2026-06-10",
    "full_name": "Test User", "base_rent_amount": 500,
    "security_deposit": 1000, "booking_advance": 500, "grand_total": 1500,
}, token=visitor_token)
check("Reject same-day booking (check_in == check_out)", status == 422, f"status={status}")

status, data = req("POST", "/public/bookings", {
    "hostel_id": hostel_id, "room_id": room_id,
    "booking_mode": "daily",
    "check_in_date": "2026-06-15", "check_out_date": "2026-06-10",
    "full_name": "Test User", "base_rent_amount": 500,
    "security_deposit": 1000, "booking_advance": 500, "grand_total": 1500,
}, token=visitor_token)
check("Reject reversed dates (check_out < check_in)", status == 422, f"status={status}")

# Valid booking — use far-future dates to avoid seed data conflicts
status, data = req("POST", "/public/bookings", {
    "hostel_id": hostel_id, "room_id": room_id,
    "booking_mode": "daily",
    "check_in_date": "2027-03-01", "check_out_date": "2027-03-10",
    "full_name": "Arun Kapoor", "base_rent_amount": 500,
    "security_deposit": 1000, "booking_advance": 500, "grand_total": 1500,
}, token=visitor_token)
check("Create valid booking", status == 201, data.get("booking_number", str(data)))
booking_id = data.get("id", "")
booking_status = data.get("status", "")
check("Booking starts as payment_pending", booking_status == "payment_pending", booking_status)

# ── 4. Admin operations ───────────────────────────────────────────────
print("\n[4] Admin Operations")
status, data = req("GET", "/admin/dashboard", token=admin_token)
check("Admin dashboard", status == 200, str(data))

status, data = req("GET", "/admin/my-hostels", token=admin_token)
check("Admin my-hostels", status == 200 and len(data) > 0, f"{len(data)} hostels")
admin_hostel_id = data[0]["id"] if data else hostel_id

status, data = req("GET", f"/admin/hostels/{admin_hostel_id}/bookings", token=admin_token)
check("Admin list bookings", status == 200, f"{len(data)} bookings")

# Approve booking — need a bed
status, beds_data = req("GET", f"/admin/hostels/{admin_hostel_id}/rooms", token=admin_token)
available_bed_id = None
if beds_data:
    for room in beds_data:
        if room.get("available_beds", 0) > 0:
            r_status, b_data = req("GET", f"/admin/rooms/{room['id']}/beds", token=admin_token)
            if b_data:
                for bed in b_data:
                    if bed.get("status") == "available":
                        available_bed_id = bed["id"]
                        break
        if available_bed_id:
            break

if booking_id and available_bed_id:
    status, data = req("PATCH", f"/admin/bookings/{booking_id}/approve",
                       {"bed_id": available_bed_id}, token=admin_token)
    check("Approve booking", status == 200, data.get("status", str(data)))
    check("Booking status → approved", data.get("status") == "approved", data.get("status"))
    check("Bed assigned to booking", data.get("bed_id") == available_bed_id, data.get("bed_id"))

    # Try to double-book same bed same dates — must be rejected
    status, data2 = req("POST", "/public/bookings", {
        "hostel_id": hostel_id, "room_id": room_id,
        "booking_mode": "daily",
        "check_in_date": "2027-03-01", "check_out_date": "2027-03-10",
        "full_name": "Another User", "base_rent_amount": 500,
        "security_deposit": 1000, "booking_advance": 500, "grand_total": 1500,
        "bed_id": available_bed_id,
    }, token=visitor_token)
    booking2_id = data2.get("id", "")
    if booking2_id:
        status2, data3 = req("PATCH", f"/admin/bookings/{booking2_id}/approve",
                             {"bed_id": available_bed_id}, token=admin_token)
        check("Reject double-booking same bed+dates", status2 == 409, f"status={status2}")
else:
    print(f"  - Skipping approval tests (no available bed found)")

# ── 5. Tenancy enforcement ────────────────────────────────────────────
print("\n[5] Tenancy Enforcement")

# Get a hostel the admin does NOT own
status, all_hostels = req("GET", "/super-admin/hostels", token=sa_token)
other_hostel_id = None
if all_hostels:
    for h in all_hostels:
        if h["id"] != admin_hostel_id:
            other_hostel_id = h["id"]
            break

if other_hostel_id:
    status, data = req("GET", f"/admin/hostels/{other_hostel_id}/bookings", token=admin_token)
    check("Admin blocked from other hostel", status == 403, f"status={status}")
else:
    print("  - Skipping tenancy test (only 1 hostel)")

# ── 6. Role enforcement ───────────────────────────────────────────────
print("\n[6] Role Enforcement")
status, data = req("GET", "/super-admin/dashboard", token=visitor_token)
check("Visitor blocked from super-admin", status == 403, f"status={status}")

status, data = req("GET", "/admin/dashboard", token=student_token)
check("Student blocked from admin", status == 403, f"status={status}")

status, data = req("GET", "/student/profile", token=admin_token)
check("Admin blocked from student profile", status == 403, f"status={status}")

# ── 7. Super admin ────────────────────────────────────────────────────

print("\n[7] Super Admin")
status, data = req("GET", "/super-admin/dashboard", token=sa_token)
check("Super admin dashboard", status == 200, str(data))

status, data = req("GET", "/super-admin/hostels", token=sa_token)
check("Super admin hostel list", status == 200 and len(data) > 0, f"{len(data)} hostels")

status, data = req("GET", "/super-admin/admins", token=sa_token)
check("Super admin admin list", status == 200, f"{len(data)} admins")

status, data = req("GET", "/super-admin/subscriptions", token=sa_token)
check("Super admin subscriptions", status == 200, f"{len(data)} subscriptions")

# ── 8. Student self-service ───────────────────────────────────────────

print("\n[8] Student Self-Service")
status, data = req("GET", "/student/profile", token=student_token)
check("Student profile", status == 200, data.get("student_number", str(data)))

status, data = req("GET", "/student/bookings", token=student_token)
check("Student bookings", status == 200, f"{len(data)} bookings")

status, data = req("GET", "/student/payments", token=student_token)
check("Student payments", status == 200, f"{len(data)} payments")

status, data = req("GET", "/student/attendance", token=student_token)
check("Student attendance", status == 200, f"{len(data)} records")

status, data = req("GET", "/student/notices", token=student_token)
check("Student notices", status == 200, f"{len(data)} notices")

status, data = req("GET", "/student/mess-menu", token=student_token)
check("Student mess menu", status == 200, f"{len(data)} menus")

status, data = req("GET", "/student/complaints", token=student_token)
check("Student complaints", status == 200, f"{len(data)} complaints")

# ── 9. Supervisor ─────────────────────────────────────────────────────
print("\n[9] Supervisor")
status, sup_login = req("POST", "/auth/login", {"email_or_phone": "supervisor1@stayease.com", "password": "Test@1234"})
sup_token = sup_login.get("access_token", "")

status, data = req("GET", "/supervisor/dashboard", token=sup_token)
check("Supervisor dashboard", status == 200, str(data))

status, data = req("GET", "/supervisor/students", token=sup_token)
check("Supervisor students", status == 200, f"{len(data)} students")

status, data = req("GET", "/supervisor/complaints", token=sup_token)
check("Supervisor complaints", status == 200, f"{len(data)} complaints")

status, data = req("GET", "/supervisor/attendance", token=sup_token)
check("Supervisor attendance", status == 200, f"{len(data)} records")

status, data = req("GET", "/supervisor/maintenance", token=sup_token)
check("Supervisor maintenance", status == 200, f"{len(data)} requests")

status, data = req("GET", "/supervisor/notices", token=sup_token)
check("Supervisor notices", status == 200, f"{len(data)} notices")

status, data = req("GET", "/supervisor/mess-menu", token=sup_token)
check("Supervisor mess menu", status == 200, f"{len(data)} menus")

print("\n" + "=" * 60)
print("  Test suite complete.")
print("=" * 60 + "\n")
