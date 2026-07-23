# fix_student_routes.py
#!/usr/bin/env python3
"""
Diagnostic and Fix Script for Student Routes
Run: python scripts/fix_student_routes.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta

BASE_URL = "http://localhost:8000/api/v1"

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_success(text: str):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    print(f"{RED}✗ {text}{RESET}")


def print_info(text: str):
    print(f"{BLUE}ℹ {text}{RESET}")


def print_section(title: str):
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}{title:^70}{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")


def make_request(method: str, path: str, token: str = None, body: dict = None) -> tuple:
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {"detail": str(e)}
        except:
            return e.code, {"detail": raw.decode('utf-8', errors='replace')}
    except Exception as e:
        return 500, {"detail": str(e)}


def login(email: str, password: str = "Test@1234") -> str:
    status, data = make_request("POST", "/auth/login", body={
        "email_or_phone": email,
        "password": password
    })
    if status == 200:
        return data.get("access_token")
    return None


def diagnose_notice_read_status():
    """Diagnose the /student/notices/read-status endpoint"""
    print_section("DIAGNOSING: GET /student/notices/read-status")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print_error("Failed to login as student")
        return
    
    # Step 1: Get notices first
    print_info("Step 1: Fetching notices...")
    status, notices = make_request("GET", "/student/notices/paginated?page=1&per_page=5", token=token)
    
    if status != 200:
        print_error(f"Failed to fetch notices: {status}")
        return
    
    items = notices.get("items", [])
    print_info(f"Found {len(items)} notices")
    
    if items:
        print_info(f"Sample notice: {items[0].get('title', 'N/A')[:50]}")
    
    # Step 2: Try to mark a notice as read
    if items:
        notice_id = items[0].get("id")
        print_info(f"Step 2: Marking notice {notice_id[:8]}... as read")
        status, data = make_request("POST", f"/student/notices/{notice_id}/read", token=token)
        
        if status == 200:
            print_success(f"Notice marked as read: {data}")
        else:
            print_error(f"Failed to mark notice as read: {status} - {data.get('detail', '')}")
    
    # Step 3: Get read status
    print_info("Step 3: Getting read status...")
    status, data = make_request("GET", "/student/notices/read-status", token=token)
    
    if status == 200:
        print_success(f"Read status endpoint returned: {len(data)} read notices")
        print_info(f"Read notice IDs: {data[:3] if data else []}")
    else:
        print_error(f"Read status endpoint failed: {status}")
        print_info(f"Error details: {data.get('detail', 'Unknown')}")
        
        # Try to see if it's a database issue
        print_info("\nTrying direct database query simulation...")
        # Check if notice_reads table has records
        status, history = make_request("GET", "/student/notices/paginated?page=1&per_page=1", token=token)
        if status == 200 and history.get("items"):
            first_notice = history["items"][0]
            print_info(f"Notice ID: {first_notice.get('id')}")
            print_info(f"Is read in response: {first_notice.get('is_read', False)}")
    
    return


def diagnose_leave_request():
    """Diagnose the /student/leave-request endpoint"""
    print_section("DIAGNOSING: POST /student/leave-request")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print_error("Failed to login as student")
        return
    
    # Step 1: Get student profile to verify student exists
    print_info("Step 1: Getting student profile...")
    status, profile = make_request("GET", "/student/profile", token=token)
    
    if status != 200:
        print_error(f"Failed to get student profile: {status}")
        return
    
    student_id = profile.get("id")
    hostel_id = profile.get("hostel_id")
    print_info(f"Student ID: {student_id}")
    print_info(f"Hostel ID: {hostel_id}")
    
    # Step 2: Try to create a leave request with valid dates
    future_date = (date.today() + timedelta(days=2)).isoformat()
    future_end = (date.today() + timedelta(days=5)).isoformat()
    
    print_info(f"Step 2: Creating leave request from {future_date} to {future_end}")
    
    payload = {
        "from_date": future_date,
        "to_date": future_end,
        "reason": "Medical leave - diagnostic test"
    }
    
    status, data = make_request("POST", "/student/leave-request", token=token, body=payload)
    
    if status == 201:
        print_success(f"Leave request created: {data}")
        return
    else:
        print_error(f"Leave request failed: {status}")
        print_info(f"Error: {data.get('detail', 'Unknown')}")
        
        # Try alternative approach - create complaint directly
        print_info("\nTrying alternative: Create complaint directly...")
        complaint_payload = {
            "category": "other",
            "title": f"Leave Request: {future_date} to {future_end}",
            "description": f"Leave from {future_date} to {future_end}. Reason: Medical leave",
            "priority": "low"
        }
        
        status2, data2 = make_request("POST", "/student/complaints", token=token, body=complaint_payload)
        
        if status2 == 201:
            print_success(f"Complaint created successfully as alternative")
            print_info(f"Complaint ID: {data2.get('id')}")
        else:
            print_error(f"Direct complaint also failed: {status2}")
            print_info(f"Error: {data2.get('detail', 'Unknown')}")
        
        return


def check_database_connection():
    """Check if database connection is working"""
    print_section("CHECKING DATABASE CONNECTION")
    
    # Try to access various endpoints that hit the database
    endpoints = [
        ("GET", "/public/hostels?per_page=1", "Public hostels"),
        ("GET", "/public/cities", "Cities list"),
    ]
    
    for method, path, name in endpoints:
        status, data = make_request(method, path)
        if status == 200:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: Failed (HTTP {status})")
    
    # Check admin endpoints with auth
    token = login("admin1@leviticanestora.com")
    if token:
        status, data = make_request("GET", "/admin/my-hostels", token=token)
        if status == 200:
            print_success("Admin hostels: OK")
        else:
            print_error(f"Admin hostels: Failed (HTTP {status}")
    
    return


def test_notice_read_status_fix():
    """Test the notice read status endpoint with detailed logging"""
    print_section("TESTING: GET /student/notices/read-status (Detailed)")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print_error("Failed to login")
        return
    
    # Make request with detailed error handling
    url = f"{BASE_URL}/student/notices/read-status"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            data = json.loads(raw) if raw else {}
            print_success(f"Status 200: Found {len(data)} read notices")
            print_info(f"Response type: {type(data)}")
            if isinstance(data, list):
                print_info(f"Sample IDs: {data[:3]}")
    except urllib.error.HTTPError as e:
        print_error(f"HTTP Error {e.code}")
        raw = e.read()
        try:
            error_data = json.loads(raw)
            print_info(f"Error detail: {error_data.get('detail', 'Unknown')}")
            if 'detail' in error_data:
                print_info(f"Full error: {error_data}")
        except:
            print_info(f"Raw error: {raw.decode('utf-8', errors='replace')}")
    except Exception as e:
        print_error(f"Other error: {e}")
    
    return


def test_leave_request_fix():
    """Test leave request with minimal payload"""
    print_section("TESTING: POST /student/leave-request (Detailed)")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print_error("Failed to login")
        return
    
    # Test with minimal valid payload
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    day_after = (date.today() + timedelta(days=3)).isoformat()
    
    payload = {
        "from_date": tomorrow,
        "to_date": day_after,
        "reason": "Test leave"
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    url = f"{BASE_URL}/student/leave-request"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            result = json.loads(raw) if raw else {}
            print_success(f"Status {resp.status}: {result.get('message', 'Success')}")
            if result.get('reference'):
                print_info(f"Reference: {result.get('reference')}")
    except urllib.error.HTTPError as e:
        print_error(f"HTTP Error {e.code}")
        raw = e.read()
        try:
            error_data = json.loads(raw)
            print_info(f"Error detail: {error_data.get('detail', 'Unknown')}")
            # Check for specific errors
            detail = error_data.get('detail', '')
            if 'student' in detail.lower():
                print_info("Issue: Student profile not found")
            elif 'complaint' in detail.lower():
                print_info("Issue: Complaint creation failed")
            elif 'date' in detail.lower():
                print_info("Issue: Date validation failed")
        except:
            print_info(f"Raw error: {raw.decode('utf-8', errors='replace')}")
    except Exception as e:
        print_error(f"Other error: {e}")
    
    return


def fix_notice_read_status():
    """Provide fix for notice read status endpoint"""
    print_section("FIX: GET /student/notices/read-status")
    
    print_info("The issue is likely in NoticeService.get_user_read_notices() method")
    print_info("Check that the method returns a list of strings, not a list of objects")
    
    print_info("\nProposed fix for app/services/notice_service.py:")
    print("""
    async def get_user_read_notices(
        self,
        *,
        user_id: str,
    ) -> list[str]:
        \"\"\"Get list of notice IDs that a user has read\"\"\"
        from sqlalchemy import select
        from app.models.operations import NoticeRead
        
        result = await self.session.execute(
            select(NoticeRead.notice_id).where(NoticeRead.user_id == user_id)
        )
        # Convert UUID to string for each result
        return [str(notice_id) for notice_id in result.scalars().all()]
    """)
    
    return


def fix_leave_request():
    """Provide fix for leave request endpoint"""
    print_section("FIX: POST /student/leave-request")
    
    print_info("The issue is likely in the leave request creation logic")
    print_info("Check that the student exists and the complaint is created correctly")
    
    print_info("\nProposed fix for app/api/v1/student/routes.py:")
    print("""
    @router.post("/leave-request", status_code=201)
    async def create_leave_request(
        request: Request,
        current_user: StudentUser,
        db: DBSession
    ):
        \"\"\"Apply for leave.\"\"\"
        from app.models.student import Student
        from app.models.operations import Complaint
        from sqlalchemy import select
        import uuid
        
        body = await request.json()
        from_date = body.get("from_date")
        to_date = body.get("to_date")
        reason = body.get("reason")
        
        result = await db.execute(
            select(Student).where(Student.user_id == current_user.id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found.")
        
        leave = Complaint(
            complaint_number=f"LVE-{uuid.uuid4().hex[:6].upper()}",
            student_id=student.id,
            hostel_id=student.hostel_id,
            category="other",
            title=f"Leave Request: {from_date} to {to_date}",
            description=f"Leave from {from_date} to {to_date}. Reason: {reason}",
            priority="low",
            status="open",
        )
        db.add(leave)
        await db.commit()
        await db.refresh(leave)
        
        return {
            "message": "Leave request submitted.",
            "reference": leave.complaint_number,
            "from_date": from_date,
            "to_date": to_date
        }
    """)
    
    return


def run_fixes():
    """Run all diagnostics and fixes"""
    print_section("STUDENT ROUTES FIX SCRIPT")
    
    # Check database connection
    check_database_connection()
    
    # Diagnose notice read status
    diagnose_notice_read_status()
    test_notice_read_status_fix()
    fix_notice_read_status()
    
    # Diagnose leave request
    diagnose_leave_request()
    test_leave_request_fix()
    fix_leave_request()
    
    print_section("SUMMARY")
    print(f"""
{YELLOW}Issues Found:{RESET}
  1. GET /student/notices/read-status - Returns HTTP 500
  2. POST /student/leave-request - Returns HTTP 500

{YELLOW}Likely Causes:{RESET}
  1. Notice read status: The service method may be returning UUID objects
     instead of strings, or the NoticeRead table may have data issues
  2. Leave request: The leave request creation logic may have issues
     with the Complaint model or database constraints

{YELLOW}Suggested Fixes:{RESET}
  1. Update NoticeService.get_user_read_notices() to convert UUIDs to strings
  2. Ensure Student exists before creating leave request
  3. Add better error handling and logging

{GREEN}To apply fixes manually:{RESET}
  1. Edit app/services/notice_service.py
  2. Edit app/api/v1/student/routes.py
  3. Restart the backend: uvicorn app.main:app --reload
  4. Run the test script again
    """)


if __name__ == "__main__":
    run_fixes()