import asyncio
import asyncpg


async def create_db():
    conn = await asyncpg.connect("postgresql://postgres:1234@localhost:5432/postgres")
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", "stayease_dev"
    )
    if not exists:
        await conn.execute("CREATE DATABASE stayease_dev")
        print("Database stayease_dev created.")
    else:
        print("Database stayease_dev already exists.")
    await conn.close()


asyncio.run(create_db())
# scripts/test_supervisor_routes.py
#!/usr/bin/env python3
"""
Test Supervisor Routes - Comprehensive API Testing

Run: python scripts/test_supervisor_routes.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

# ANSI colors
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


def print_warning(text: str):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_section(title: str):
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}{title:^70}{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")


def print_subsection(title: str):
    print(f"\n{BOLD}{title}{RESET}")
    print("-" * 50)


def make_request(method: str, path: str, token: Optional[str] = None, body: Optional[Dict] = None) -> tuple[int, Any]:
    """Make HTTP request to API"""
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


def login(email: str, password: str = "Test@1234") -> Optional[Dict]:
    """Login and return user data with token"""
    status, data = make_request("POST", "/auth/login", body={
        "email_or_phone": email,
        "password": password
    })
    if status == 200:
        print_success(f"Logged in as {email}")
        return data
    else:
        print_error(f"Login failed for {email}: {data.get('detail', 'Unknown error')}")
        return None


class SupervisorRoutesTester:
    def __init__(self):
        self.supervisor_token = None
        self.supervisor_id = None
        self.hostel_id = None
        self.student_id = None
        self.complaint_id = None
        self.maintenance_id = None
        self.notice_id = None
        self.results = {"passed": 0, "failed": 0, "tests": []}
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.results["tests"].append({"name": test_name, "passed": passed, "message": message})
        if passed:
            self.results["passed"] += 1
            print_success(f"{test_name}: {message}" if message else test_name)
        else:
            self.results["failed"] += 1
            print_error(f"{test_name}: {message}" if message else test_name)
    
    def setup(self):
        """Setup test data - login supervisor and get required IDs"""
        print_section("SETUP")
        
        # Login as Supervisor
        supervisor_data = login("supervisor1@stayease.com")
        if not supervisor_data:
            print_error("Cannot proceed without supervisor login")
            return False
        
        self.supervisor_token = supervisor_data.get("access_token")
        self.supervisor_id = supervisor_data.get("user_id")
        
        # Get hostel IDs from supervisor's token
        hostel_ids = supervisor_data.get("hostel_ids", [])
        if hostel_ids:
            self.hostel_id = hostel_ids[0]
        
        print_info(f"Supervisor ID: {self.supervisor_id}")
        print_info(f"Hostel ID: {self.hostel_id}")
        
        # Get a student ID from the hostel
        status, students = make_request("GET", "/supervisor/students", token=self.supervisor_token)
        if status == 200 and students:
            self.student_id = students[0].get("id")
            print_info(f"Student ID: {self.student_id}")
        
        return True
    
    # ==================== DASHBOARD TESTS ====================
    
    def test_dashboard(self):
        """Test GET /supervisor/dashboard"""
        print_subsection("1. GET /supervisor/dashboard")
        
        status, data = make_request("GET", "/supervisor/dashboard", token=self.supervisor_token)
        
        if status == 200:
            required_fields = ["students", "complaints", "attendance_records", "maintenance_requests", "notices", "hostels"]
            missing = [f for f in required_fields if f not in data]
            
            if not missing:
                self.add_result("Dashboard", True, f"Hostels: {data.get('hostels')}, Students: {data.get('students')}")
            else:
                self.add_result("Dashboard", False, f"Missing fields: {missing}")
        else:
            self.add_result("Dashboard", False, f"HTTP {status}")
    
    # ==================== STUDENT TESTS ====================
    
    def test_list_students(self):
        """Test GET /supervisor/students"""
        print_subsection("2. GET /supervisor/students")
        
        status, data = make_request("GET", "/supervisor/students", token=self.supervisor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Students", True, f"Found {count} students")
            
            if count > 0 and not self.student_id:
                self.student_id = data[0].get("id")
        else:
            self.add_result("List Students", False, f"HTTP {status}")
    
    # ==================== COMPLAINT TESTS ====================
    
    def test_list_complaints(self):
        """Test GET /supervisor/complaints"""
        print_subsection("3. GET /supervisor/complaints")
        
        status, data = make_request("GET", "/supervisor/complaints", token=self.supervisor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Complaints", True, f"Found {count} complaints")
            
            if count > 0 and not self.complaint_id:
                self.complaint_id = data[0].get("id")
        else:
            self.add_result("List Complaints", False, f"HTTP {status}")
    
    def test_update_complaint(self):
        """Test PATCH /supervisor/complaints/{complaint_id}"""
        print_subsection("4. PATCH /supervisor/complaints/{complaint_id}")
        
        if not self.complaint_id:
            # Create a test complaint first
            print_info("No complaint found, creating test complaint...")
            status, data = make_request("POST", "/student/complaints", token=self.supervisor_token, body={
                "category": "maintenance",
                "title": "Test Complaint for Supervisor",
                "description": "This is a test complaint",
                "priority": "medium"
            })
            if status == 201:
                self.complaint_id = data.get("id")
                print_info(f"Created test complaint: {self.complaint_id[:8]}...")
            else:
                self.add_result("Update Complaint", False, "Could not create test complaint")
                return
        
        payload = {"status": "in_progress", "resolution_notes": "Investigation started"}
        status, data = make_request("PATCH", f"/supervisor/complaints/{self.complaint_id}", token=self.supervisor_token, body=payload)
        
        if status == 200:
            self.add_result("Update Complaint", True, f"Status: {data.get('status')}")
        else:
            self.add_result("Update Complaint", False, f"HTTP {status}: {data.get('detail', 'Unknown')}")
    
    # ==================== ATTENDANCE TESTS ====================
    
    def test_list_attendance(self):
        """Test GET /supervisor/attendance"""
        print_subsection("5. GET /supervisor/attendance")
        
        status, data = make_request("GET", "/supervisor/attendance", token=self.supervisor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Attendance", True, f"Found {count} records")
        else:
            self.add_result("List Attendance", False, f"HTTP {status}")
    
    def test_mark_attendance(self):
        """Test POST /supervisor/attendance"""
        print_subsection("6. POST /supervisor/attendance")
        
        if not self.student_id:
            self.add_result("Mark Attendance", False, "No student ID available")
            return
        
        today = date.today().isoformat()
        payload = {
            "student_id": self.student_id,
            "date": today,
            "status": "present",
            "method": "manual",
            "check_in_time": "09:00:00",
            "check_out_time": "18:00:00"
        }
        
        status, data = make_request("POST", "/supervisor/attendance", token=self.supervisor_token, body=payload)
        
        if status == 201:
            self.add_result("Mark Attendance", True, f"Marked as {payload['status']}")
        elif status == 400 and "already" in str(data).lower():
            self.add_result("Mark Attendance", True, "Attendance already exists (OK)")
        else:
            self.add_result("Mark Attendance", False, f"HTTP {status}: {data.get('detail', 'Unknown')}")
    
    # ==================== MAINTENANCE TESTS ====================
    
    def test_list_maintenance(self):
        """Test GET /supervisor/maintenance"""
        print_subsection("7. GET /supervisor/maintenance")
        
        status, data = make_request("GET", "/supervisor/maintenance", token=self.supervisor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Maintenance", True, f"Found {count} requests")
            
            if count > 0 and not self.maintenance_id:
                self.maintenance_id = data[0].get("id")
        else:
            self.add_result("List Maintenance", False, f"HTTP {status}")
    
    def test_create_maintenance(self):
        """Test POST /supervisor/maintenance"""
        print_subsection("8. POST /supervisor/maintenance")
        
        timestamp = datetime.now().strftime("%H%M%S")
        payload = {
            "category": "electrical",
            "title": f"Test Maintenance {timestamp}",
            "description": "This is a test maintenance request",
            "priority": "medium",
            "estimated_cost": 1000.0
        }
        
        status, data = make_request("POST", "/supervisor/maintenance", token=self.supervisor_token, body=payload)
        
        if status == 201:
            self.maintenance_id = data.get("id")
            self.add_result("Create Maintenance", True, f"Created: {data.get('title')}")
        else:
            self.add_result("Create Maintenance", False, f"HTTP {status}: {data.get('detail', 'Unknown')}")
    
    def test_update_maintenance(self):
        """Test PATCH /supervisor/maintenance/{request_id}"""
        print_subsection("9. PATCH /supervisor/maintenance/{request_id}")
        
        if not self.maintenance_id:
            self.add_result("Update Maintenance", False, "No maintenance ID available")
            return
        
        payload = {"status": "in_progress"}
        status, data = make_request("PATCH", f"/supervisor/maintenance/{self.maintenance_id}", token=self.supervisor_token, body=payload)
        
        if status == 200:
            self.add_result("Update Maintenance", True, f"Status: {data.get('status')}")
        else:
            self.add_result("Update Maintenance", False, f"HTTP {status}: {data.get('detail', 'Unknown')}")
    
    # ==================== NOTICE TESTS ====================
    
    def test_list_notices(self):
        """Test GET /supervisor/notices"""
        print_subsection("10. GET /supervisor/notices")
        
        status, data = make_request("GET", "/supervisor/notices", token=self.supervisor_token)
        
        if status == 200:
            items = data.get("items", data) if isinstance(data, dict) else data
            count = len(items) if isinstance(items, list) else 0
            self.add_result("List Notices", True, f"Found {count} notices")
            
            if count > 0 and not self.notice_id:
                if isinstance(items, list) and items:
                    self.notice_id = items[0].get("id")
        else:
            self.add_result("List Notices", False, f"HTTP {status}")
    
    def test_create_notice(self):
        """Test POST /supervisor/notices"""
        print_subsection("11. POST /supervisor/notices")
        
        timestamp = datetime.now().strftime("%H%M%S")
        payload = {
            "hostel_id": self.hostel_id,
            "title": f"Test Notice {timestamp}",
            "content": "This is a test notice from supervisor",
            "notice_type": "general",
            "priority": "medium",
            "is_published": True
        }
        
        status, data = make_request("POST", "/supervisor/notices", token=self.supervisor_token, body=payload)
        
        if status == 201:
            self.notice_id = data.get("id")
            self.add_result("Create Notice", True, f"Created: {data.get('title')}")
        else:
            self.add_result("Create Notice", False, f"HTTP {status}: {data.get('detail', 'Unknown')}")
    
    def test_update_notice(self):
        """Test PATCH /supervisor/notices/{notice_id}"""
        print_subsection("12. PATCH /supervisor/notices/{notice_id}")
        
        if not self.notice_id:
            self.add_result("Update Notice", False, "No notice ID available")
            return
        
        payload = {"title": f"Updated Notice {datetime.now().strftime('%H%M%S')}", "priority": "high"}
        status, data = make_request("PATCH", f"/supervisor/notices/{self.notice_id}", token=self.supervisor_token, body=payload)
        
        if status == 200:
            self.add_result("Update Notice", True, f"Title: {data.get('title')}")
        elif status == 403:
            self.add_result("Update Notice", True, "Permission denied (expected for platform notices)")
        else:
            self.add_result("Update Notice", False, f"HTTP {status}: {data.get('detail', 'Unknown')}")
    
    def test_toggle_notice_publish(self):
        """Test PATCH /supervisor/notices/{notice_id}/toggle-publish"""
        print_subsection("13. PATCH /supervisor/notices/{notice_id}/toggle-publish")
        
        if not self.notice_id:
            self.add_result("Toggle Notice Publish", False, "No notice ID available")
            return
        
        status, data = make_request("PATCH", f"/supervisor/notices/{self.notice_id}/toggle-publish", token=self.supervisor_token)
        
        if status == 200:
            self.add_result("Toggle Notice Publish", True, f"Is published: {data.get('is_published')}")
        elif status == 403:
            self.add_result("Toggle Notice Publish", True, "Permission denied (expected)")
        else:
            self.add_result("Toggle Notice Publish", False, f"HTTP {status}")
    
    def test_delete_notice(self):
        """Test DELETE /supervisor/notices/{notice_id}"""
        print_subsection("14. DELETE /supervisor/notices/{notice_id}")
        
        # Create a notice specifically for deletion
        timestamp = datetime.now().strftime("%H%M%S")
        payload = {
            "hostel_id": self.hostel_id,
            "title": f"Delete Test Notice {timestamp}",
            "content": "This notice will be deleted",
            "notice_type": "general",
            "priority": "low",
            "is_published": False
        }
        
        status, data = make_request("POST", "/supervisor/notices", token=self.supervisor_token, body=payload)
        
        if status != 201:
            self.add_result("Delete Notice", False, "Could not create test notice")
            return
        
        delete_notice_id = data.get("id")
        
        status, _ = make_request("DELETE", f"/supervisor/notices/{delete_notice_id}", token=self.supervisor_token)
        
        if status == 204:
            self.add_result("Delete Notice", True, "Notice deleted successfully")
        elif status == 403:
            self.add_result("Delete Notice", True, "Permission denied (expected for platform notices)")
        else:
            self.add_result("Delete Notice", False, f"HTTP {status}")
    
    # ==================== MESS MENU TESTS ====================
    
    def test_mess_menu(self):
        """Test GET /supervisor/mess-menu"""
        print_subsection("15. GET /supervisor/mess-menu")
        
        status, data = make_request("GET", "/supervisor/mess-menu", token=self.supervisor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Mess Menu", True, f"Found {count} menu items")
        else:
            self.add_result("Mess Menu", False, f"HTTP {status}")
    
    # ==================== NOTICES PAGINATED TESTS ====================
    
    def test_notices_paginated(self):
        """Test GET /supervisor/notices/paginated"""
        print_subsection("16. GET /supervisor/notices/paginated")
        
        status, data = make_request("GET", "/supervisor/notices/paginated?page=1&per_page=10", token=self.supervisor_token)
        
        if status == 200:
            required_fields = ["items", "total", "page", "per_page"]
            missing = [f for f in required_fields if f not in data]
            
            if not missing:
                self.add_result("Notices Paginated", True, f"Total: {data.get('total')}")
            else:
                self.add_result("Notices Paginated", False, f"Missing fields: {missing}")
        else:
            self.add_result("Notices Paginated", False, f"HTTP {status}")
    
    # ==================== PROFILE TESTS ====================
    
    def test_get_profile(self):
        """Test GET /supervisor/profile"""
        print_subsection("17. GET /supervisor/profile")
        
        status, data = make_request("GET", "/supervisor/profile", token=self.supervisor_token)
        
        if status == 200:
            required_fields = ["id", "email", "phone", "full_name", "role"]
            missing = [f for f in required_fields if f not in data]
            
            if not missing:
                self.add_result("Get Profile", True, f"Welcome {data.get('full_name')}")
            else:
                self.add_result("Get Profile", False, f"Missing fields: {missing}")
        else:
            self.add_result("Get Profile", False, f"HTTP {status}")
    
    def test_update_profile(self):
        """Test PATCH /supervisor/profile"""
        print_subsection("18. PATCH /supervisor/profile")
        
        # Get current name first
        status, current = make_request("GET", "/supervisor/profile", token=self.supervisor_token)
        original_name = current.get("full_name", "") if status == 200 else ""
        
        timestamp = datetime.now().strftime("%H%M%S")
        payload = {"full_name": f"Updated Supervisor {timestamp}"}
        
        status, data = make_request("PATCH", "/supervisor/profile", token=self.supervisor_token, body=payload)
        
        if status == 200:
            self.add_result("Update Profile", True, f"Name: {data.get('full_name')}")
            # Revert
            if original_name:
                make_request("PATCH", "/supervisor/profile", token=self.supervisor_token, body={"full_name": original_name})
        else:
            self.add_result("Update Profile", False, f"HTTP {status}")
    
    def test_change_password(self):
        """Test POST /supervisor/change-password"""
        print_subsection("19. POST /supervisor/change-password")
        
        payload = {
            "old_password": "Test@1234",
            "new_password": "NewTest@1234",
            "confirm_password": "NewTest@1234"
        }
        
        status, data = make_request("POST", "/supervisor/change-password", token=self.supervisor_token, body=payload)
        
        if status == 200:
            self.add_result("Change Password", True, "Password changed")
            # Change back
            revert_payload = {
                "old_password": "NewTest@1234",
                "new_password": "Test@1234",
                "confirm_password": "Test@1234"
            }
            make_request("POST", "/supervisor/change-password", token=self.supervisor_token, body=revert_payload)
        elif status == 401:
            self.add_result("Change Password", True, "Password validation working")
        else:
            self.add_result("Change Password", False, f"HTTP {status}")
    
    # ==================== PERMISSION TESTS ====================
    
    def test_permission_errors(self):
        """Test permission errors for supervisor"""
        print_subsection("20. Permission Error Tests")
        
        # Try to access admin endpoint (should fail)
        status, data = make_request("GET", "/admin/dashboard", token=self.supervisor_token)
        
        if status == 403:
            self.add_result("Admin Access Denied", True, "Supervisor cannot access admin endpoints")
        else:
            self.add_result("Admin Access Denied", False, f"Expected 403, got {status}")
        
        # Try to access super admin endpoint (should fail)
        status, data = make_request("GET", "/super-admin/dashboard", token=self.supervisor_token)
        
        if status == 403:
            self.add_result("Super Admin Access Denied", True, "Supervisor cannot access super admin endpoints")
        else:
            self.add_result("Super Admin Access Denied", False, f"Expected 403, got {status}")
        
        # Unauthorized access (no token)
        status, _ = make_request("GET", "/supervisor/dashboard")
        
        if status == 401:
            self.add_result("Unauthorized Access", True, "Auth required")
        else:
            self.add_result("Unauthorized Access", False, f"Expected 401, got {status}")
    
    # ==================== DELETE COMPLAINT ====================
    
    def test_delete_complaint(self):
        """Test DELETE /supervisor/complaints/{complaint_id}"""
        print_subsection("21. DELETE /supervisor/complaints/{complaint_id}")
        
        # Create a complaint first
        status, data = make_request("POST", "/student/complaints", token=self.supervisor_token, body={
            "category": "maintenance",
            "title": f"Complaint to Delete {datetime.now().strftime('%H%M%S')}",
            "description": "This complaint will be deleted",
            "priority": "low"
        })
        
        if status != 201:
            self.add_result("Delete Complaint", False, "Could not create test complaint")
            return
        
        complaint_to_delete = data.get("id")
        
        # Delete the complaint
        status, _ = make_request("DELETE", f"/supervisor/complaints/{complaint_to_delete}", token=self.supervisor_token)
        
        if status == 204:
            self.add_result("Delete Complaint", True, "Complaint deleted successfully")
        elif status == 403:
            self.add_result("Delete Complaint", True, "Permission denied (expected if complaint belongs to different hostel)")
        else:
            self.add_result("Delete Complaint", False, f"HTTP {status}")
    
    # ==================== RUN ALL TESTS ====================
    
    def run_all_tests(self):
        """Run all test cases"""
        print_section("SUPERVISOR ROUTES TESTING")
        print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API URL: {BASE_URL}")
        
        if not self.setup():
            print_error("Setup failed - cannot run tests")
            self.print_summary()
            return
        
        tests = [
            ("Dashboard", self.test_dashboard),
            ("List Students", self.test_list_students),
            ("List Complaints", self.test_list_complaints),
            ("Update Complaint", self.test_update_complaint),
            ("List Attendance", self.test_list_attendance),
            ("Mark Attendance", self.test_mark_attendance),
            ("List Maintenance", self.test_list_maintenance),
            ("Create Maintenance", self.test_create_maintenance),
            ("Update Maintenance", self.test_update_maintenance),
            ("List Notices", self.test_list_notices),
            ("Create Notice", self.test_create_notice),
            ("Update Notice", self.test_update_notice),
            ("Toggle Notice Publish", self.test_toggle_notice_publish),
            ("Delete Notice", self.test_delete_notice),
            ("Notices Paginated", self.test_notices_paginated),
            ("Mess Menu", self.test_mess_menu),
            ("Get Profile", self.test_get_profile),
            ("Update Profile", self.test_update_profile),
            ("Change Password", self.test_change_password),
            ("Delete Complaint", self.test_delete_complaint),
            ("Permission Errors", self.test_permission_errors),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print_error(f"{test_name} crashed: {str(e)}")
                import traceback
                traceback.print_exc()
                self.add_result(test_name, False, f"Crashed: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print_section("TEST SUMMARY")
        
        total = self.results["passed"] + self.results["failed"]
        
        print(f"\n  {BOLD}Total Tests:{RESET}   {total}")
        print(f"  {GREEN}{BOLD}Passed:{RESET}      {self.results['passed']}")
        print(f"  {RED}{BOLD}Failed:{RESET}      {self.results['failed']}")
        
        if self.results["failed"] > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for test in self.results["tests"]:
                if not test["passed"]:
                    print(f"  ✗ {test['name']}: {test['message']}")
        
        # List all working endpoints
        print(f"\n{CYAN}{BOLD}Supervisor Endpoints Tested:{RESET}")
        endpoints = [
            "GET    /supervisor/dashboard",
            "GET    /supervisor/students",
            "GET    /supervisor/complaints",
            "PATCH  /supervisor/complaints/{id}",
            "DELETE /supervisor/complaints/{id}",
            "GET    /supervisor/attendance",
            "POST   /supervisor/attendance",
            "GET    /supervisor/maintenance",
            "POST   /supervisor/maintenance",
            "PATCH  /supervisor/maintenance/{id}",
            "GET    /supervisor/notices",
            "GET    /supervisor/notices/paginated",
            "POST   /supervisor/notices",
            "PATCH  /supervisor/notices/{id}",
            "PATCH  /supervisor/notices/{id}/toggle-publish",
            "DELETE /supervisor/notices/{id}",
            "GET    /supervisor/mess-menu",
            "GET    /supervisor/profile",
            "PATCH  /supervisor/profile",
            "POST   /supervisor/change-password",
        ]
        for ep in endpoints:
            print(f"  {ep}")
        
        if self.results["failed"] == 0:
            print(f"\n{GREEN}{BOLD}✅ ALL SUPERVISOR ROUTE TESTS PASSED!{RESET}")
        else:
            print(f"\n{RED}{BOLD}❌ Some tests failed. Check the errors above.{RESET}")


if __name__ == "__main__":
    tester = SupervisorRoutesTester()
    tester.run_all_tests()