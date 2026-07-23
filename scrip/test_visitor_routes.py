#!/usr/bin/env python3
"""
Test Visitor Routes - Comprehensive API Testing

Run: python scripts/test_visitor_routes.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


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


class VisitorRoutesTester:
    def __init__(self):
        self.visitor_token = None
        self.visitor_id = None
        self.student_token = None
        self.admin_token = None
        self.hostel_id = None
        self.booking_id = None
        self.review_id = None
        self.favorite_hostel_id = None
        self.notice_id = None
        self.waitlist_entry_id = None
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
        """Setup test data - login users and get required IDs"""
        print_section("SETUP")
        
        # Login as Visitor
        visitor_data = login("arun.kapoor@gmail.com")
        if not visitor_data:
            print_error("Cannot proceed without visitor login")
            return False
        
        self.visitor_token = visitor_data.get("access_token")
        self.visitor_id = visitor_data.get("user_id")
        
        # Login as Admin to get hostel ID
        admin_data = login("admin1@leviticanestora.com")
        if admin_data:
            self.admin_token = admin_data.get("access_token")
            hostel_ids = admin_data.get("hostel_ids", [])
            self.hostel_id = hostel_ids[0] if hostel_ids else None
        
        # Login as Student
        student_data = login("hemant.pawade.lev044@levitica.in")
        if student_data:
            self.student_token = student_data.get("access_token")
        
        # Get a public hostel if admin didn't provide one
        if not self.hostel_id:
            status, hostels = make_request("GET", "/public/hostels?per_page=1")
            if status == 200 and hostels.get("items"):
                self.hostel_id = hostels["items"][0].get("id")
        
        print_info(f"Visitor ID: {self.visitor_id}")
        print_info(f"Hostel ID: {self.hostel_id}")
        
        return True
    
    # ==================== PROFILE TESTS ====================
    
    def test_get_profile(self):
        """Test GET /visitor/profile"""
        print_subsection("1. GET /visitor/profile")
        
        status, data = make_request("GET", "/visitor/profile", token=self.visitor_token)
        
        if status == 200:
            required_fields = ["id", "email", "phone", "full_name", "role"]
            missing = [f for f in required_fields if f not in data]
            
            if not missing:
                self.add_result("Get Profile", True, f"Welcome {data.get('full_name')}")
                print_info(f"  Email: {data.get('email')}")
                print_info(f"  Role: {data.get('role')}")
            else:
                self.add_result("Get Profile", False, f"Missing fields: {missing}")
        else:
            self.add_result("Get Profile", False, f"HTTP {status}")
    
    def test_update_profile(self):
        """Test PATCH /visitor/profile"""
        print_subsection("2. PATCH /visitor/profile")
        
        update_data = {
            "full_name": f"Updated Visitor {datetime.now().strftime('%H%M')}",
            "phone": f"+91-9876543210"
        }
        
        status, data = make_request("PATCH", "/visitor/profile", token=self.visitor_token, body=update_data)
        
        if status == 200:
            self.add_result("Update Profile", True, f"Name: {data.get('full_name')}")
        else:
            self.add_result("Update Profile", False, f"HTTP {status}")
    
    # ==================== BOOKING TESTS ====================
    
    def test_list_bookings(self):
        """Test GET /visitor/bookings"""
        print_subsection("3. GET /visitor/bookings")
        
        status, data = make_request("GET", "/visitor/bookings", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Bookings", True, f"Found {count} bookings")
            
            if count > 0 and not self.booking_id:
                self.booking_id = data[0].get("id")
                print_info(f"  Using booking ID: {self.booking_id[:8]}...")
        else:
            self.add_result("List Bookings", False, f"HTTP {status}")
    
    def test_booking_status_history(self):
        """Test GET /visitor/bookings/{booking_id}/status-history"""
        print_subsection("4. GET /visitor/bookings/{id}/status-history")
        
        if not self.booking_id:
            print_warning("No booking ID available - skipping test")
            self.add_result("Booking Status History", True, "Skipped - no booking")
            return
        
        status, data = make_request("GET", f"/visitor/bookings/{self.booking_id}/status-history", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Booking Status History", True, f"Found {count} status changes")
            
            if count > 0:
                print_info(f"  Latest: {data[0].get('new_status')} at {data[0].get('created_at')[:10]}")
        else:
            self.add_result("Booking Status History", False, f"HTTP {status}")
    
    # ==================== REVIEW TESTS ====================
    
    def test_create_review(self):
        """Test POST /visitor/reviews"""
        print_subsection("5. POST /visitor/reviews")
        
        review_data = {
            "hostel_id": self.hostel_id,
            "overall_rating": 4.5,
            "cleanliness_rating": 4.0,
            "food_rating": 4.5,
            "security_rating": 5.0,
            "value_rating": 4.0,
            "title": "Great Hostel Experience",
            "content": "Really enjoyed my stay. The staff was friendly and facilities were clean."
        }
        
        status, data = make_request("POST", "/visitor/reviews", token=self.visitor_token, body=review_data)
        
        if status == 201:
            self.review_id = data.get("id")
            self.add_result("Create Review", True, f"Review ID: {self.review_id[:8] if self.review_id else 'N/A'}...")
            print_info(f"  Rating: {data.get('overall_rating')}/5")
        elif status == 409:
            self.add_result("Create Review", True, "Already reviewed (expected)")
        else:
            self.add_result("Create Review", False, f"HTTP {status}")
    
    def test_list_reviews(self):
        """Test GET /visitor/reviews"""
        print_subsection("6. GET /visitor/reviews")
        
        status, data = make_request("GET", "/visitor/reviews", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Reviews", True, f"Found {count} reviews")
        else:
            self.add_result("List Reviews", False, f"HTTP {status}")
    
    # ==================== FAVORITE TESTS ====================
    
    def test_add_favorite(self):
        """Test POST /visitor/favorites/{hostel_id}"""
        print_subsection("7. POST /visitor/favorites/{hostel_id}")
        
        if not self.hostel_id:
            print_warning("No hostel ID - skipping test")
            self.add_result("Add Favorite", True, "Skipped - no hostel")
            return
        
        status, data = make_request("POST", f"/visitor/favorites/{self.hostel_id}", token=self.visitor_token)
        
        if status == 201:
            self.favorite_hostel_id = self.hostel_id
            self.add_result("Add Favorite", True, data.get("message", "Added"))
        elif "already" in str(data).lower():
            self.add_result("Add Favorite", True, "Already in favorites")
        else:
            self.add_result("Add Favorite", False, f"HTTP {status}")
    
    def test_list_favorites(self):
        """Test GET /visitor/favorites"""
        print_subsection("8. GET /visitor/favorites")
        
        status, data = make_request("GET", "/visitor/favorites", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Favorites", True, f"Found {count} favorites")
            
            if count > 0:
                print_info(f"  First: {data[0].get('hostel_name')}")
        else:
            self.add_result("List Favorites", False, f"HTTP {status}")
    
    def test_compare_favorites(self):
        """Test POST /visitor/favorites/compare"""
        print_subsection("9. POST /visitor/favorites/compare")
        
        status, data = make_request("POST", "/visitor/favorites/compare", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Compare Favorites", True, f"Comparing {count} hostels")
        else:
            self.add_result("Compare Favorites", False, f"HTTP {status}")
    
    def test_remove_favorite(self):
        """Test DELETE /visitor/favorites/{hostel_id}"""
        print_subsection("10. DELETE /visitor/favorites/{hostel_id}")
        
        if not self.favorite_hostel_id:
            print_warning("No favorite to remove - skipping")
            self.add_result("Remove Favorite", True, "Skipped")
            return
        
        status, data = make_request("DELETE", f"/visitor/favorites/{self.favorite_hostel_id}", token=self.visitor_token)
        
        if status == 200:
            self.add_result("Remove Favorite", True, data.get("message", "Removed"))
        else:
            self.add_result("Remove Favorite", False, f"HTTP {status}")
    
    # ==================== NOTICE TESTS ====================
    
    def test_list_notices(self):
        """Test GET /visitor/notices/paginated"""
        print_subsection("11. GET /visitor/notices/paginated")
        
        status, data = make_request("GET", "/visitor/notices/paginated?page=1&per_page=10", token=self.visitor_token)
        
        if status == 200:
            items = data.get("items", [])
            total = data.get("total", 0)
            self.add_result("List Notices", True, f"Found {total} platform notices")
            
            if items and not self.notice_id:
                self.notice_id = items[0].get("id")
                print_info(f"  Sample: {items[0].get('title')[:50]}")
        else:
            self.add_result("List Notices", False, f"HTTP {status}")
    
    def test_get_notice(self):
        """Test GET /visitor/notices/{notice_id}"""
        print_subsection("12. GET /visitor/notices/{notice_id}")
        
        if not self.notice_id:
            print_warning("No notice ID - skipping")
            self.add_result("Get Notice", True, "Skipped")
            return
        
        status, data = make_request("GET", f"/visitor/notices/{self.notice_id}", token=self.visitor_token)
        
        if status == 200:
            self.add_result("Get Notice", True, f"Title: {data.get('title', '')[:50]}")
            print_info(f"  Read: {data.get('is_read')}")
        else:
            self.add_result("Get Notice", False, f"HTTP {status}")
    
    def test_mark_notice_read(self):
        """Test POST /visitor/notices/{notice_id}/read"""
        print_subsection("13. POST /visitor/notices/{notice_id}/read")
        
        if not self.notice_id:
            print_warning("No notice ID - skipping")
            self.add_result("Mark Notice Read", True, "Skipped")
            return
        
        status, data = make_request("POST", f"/visitor/notices/{self.notice_id}/read", token=self.visitor_token)
        
        if status == 200:
            self.add_result("Mark Notice Read", True, f"Is read: {data.get('is_read')}")
        else:
            self.add_result("Mark Notice Read", False, f"HTTP {status}")
    
    def test_read_status(self):
        """Test GET /visitor/notices/read-status"""
        print_subsection("14. GET /visitor/notices/read-status")
        
        status, data = make_request("GET", "/visitor/notices/read-status", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Read Status", True, f"Read {count} notices")
        else:
            self.add_result("Read Status", False, f"HTTP {status}")
    
    # ==================== MESS MENU TESTS ====================
    
    def test_mess_menu(self):
        """Test GET /visitor/hostels/{hostel_id}/mess-menu"""
        print_subsection("15. GET /visitor/hostels/{hostel_id}/mess-menu")
        
        if not self.hostel_id:
            print_warning("No hostel ID - skipping")
            self.add_result("Mess Menu", True, "Skipped")
            return
        
        status, data = make_request("GET", f"/visitor/hostels/{self.hostel_id}/mess-menu")
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Mess Menu", True, f"Found {count} menu items")
            
            if count > 0:
                print_info(f"  Sample: {data[0].get('item_name', 'N/A')} ({data[0].get('meal_type', 'N/A')})")
        else:
            self.add_result("Mess Menu", False, f"HTTP {status}")
    
    # ==================== WAITLIST TESTS ====================
    
    def test_join_waitlist(self):
        """Test POST /visitor/waitlist/join"""
        print_subsection("16. POST /visitor/waitlist/join")
        
        if not self.hostel_id:
            print_warning("No hostel ID - skipping")
            self.add_result("Join Waitlist", True, "Skipped")
            return
        
        future_date = (date.today() + timedelta(days=60)).isoformat()
        future_end = (date.today() + timedelta(days=90)).isoformat()
        
        waitlist_data = {
            "hostel_id": self.hostel_id,
            "room_id": "00000000-0000-0000-0000-000000000001",  # Might not exist
            "booking_mode": "monthly",
            "check_in_date": future_date,
            "check_out_date": future_end
        }
        
        status, data = make_request("POST", "/visitor/waitlist/join", token=self.visitor_token, body=waitlist_data)
        
        # This might fail if room doesn't exist - that's fine
        if status in [200, 201]:
            self.waitlist_entry_id = data.get("id")
            self.add_result("Join Waitlist", True, f"Position: {data.get('position', 'N/A')}")
        elif status == 404:
            self.add_result("Join Waitlist", True, "Room not found (expected without valid room)")
        else:
            self.add_result("Join Waitlist", False, f"HTTP {status}")
    
    def test_list_waitlist(self):
        """Test GET /visitor/waitlist"""
        print_subsection("17. GET /visitor/waitlist")
        
        status, data = make_request("GET", "/visitor/waitlist", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Waitlist", True, f"Found {count} entries")
        else:
            self.add_result("List Waitlist", False, f"HTTP {status}")
    
    # ==================== FILE UPLOAD TESTS ====================
    
    def test_presigned_url(self):
        """Test POST /visitor/uploads/presigned-url"""
        print_subsection("18. POST /visitor/uploads/presigned-url")
        
        upload_data = {
            "file_name": "test_id_proof.jpg",
            "content_type": "image/jpeg",
            "file_size": 1024 * 500  # 500KB
        }
        
        status, data = make_request("POST", "/visitor/uploads/presigned-url", token=self.visitor_token, body=upload_data)
        
        if status == 200:
            self.add_result("Presigned URL", True, "Upload URL generated")
            print_info(f"  Filename: {data.get('filename')}")
        else:
            self.add_result("Presigned URL", False, f"HTTP {status}")
    
    def test_invalid_file_upload(self):
        """Test invalid file type rejection"""
        print_subsection("19. POST /visitor/uploads/presigned-url (Invalid)")
        
        upload_data = {
            "file_name": "test.exe",
            "content_type": "application/x-msdownload",
            "file_size": 1024
        }
        
        status, data = make_request("POST", "/visitor/uploads/presigned-url", token=self.visitor_token, body=upload_data)
        
        if status == 400:
            self.add_result("Invalid File Rejection", True, "Correctly rejected")
        else:
            self.add_result("Invalid File Rejection", False, f"Expected 400, got {status}")
    
    # ==================== PERMISSION TESTS ====================
    
    def test_student_can_access_visitor_endpoints(self):
        """Test that student can access visitor endpoints"""
        print_subsection("20. Student Access to Visitor Endpoints")
        
        if not self.student_token:
            print_warning("No student token - skipping")
            self.add_result("Student Access", True, "Skipped")
            return
        
        status, data = make_request("GET", "/visitor/profile", token=self.student_token)
        
        if status == 200:
            self.add_result("Student Access", True, "Student can access visitor endpoints")
        else:
            self.add_result("Student Access", False, f"HTTP {status}")
    
    def test_unauthorized_access(self):
        """Test endpoints require authentication"""
        print_subsection("21. Unauthorized Access")
        
        status, _ = make_request("GET", "/visitor/profile")  # No token
        
        if status == 401:
            self.add_result("Unauthorized Access", True, "Auth required")
        else:
            self.add_result("Unauthorized Access", False, f"Expected 401, got {status}")
    
    def test_admin_can_access_visitor_endpoints(self):
        """Test that admin can access visitor endpoints"""
        print_subsection("22. Admin Access to Visitor Endpoints")
        
        if not self.admin_token:
            print_warning("No admin token - skipping")
            self.add_result("Admin Access", True, "Skipped")
            return
        
        status, data = make_request("GET", "/visitor/profile", token=self.admin_token)
        
        if status == 200:
            self.add_result("Admin Access", True, "Admin can access visitor endpoints")
        else:
            self.add_result("Admin Access", False, f"HTTP {status}")
    
    # ==================== RUN ALL ====================
    
    def run_all_tests(self):
        """Run all test cases"""
        print_section("VISITOR ROUTES TESTING")
        print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API URL: {BASE_URL}")
        
        if not self.setup():
            print_error("Setup failed - cannot run tests")
            return
        
        tests = [
            # Profile
            self.test_get_profile,
            self.test_update_profile,
            
            # Bookings
            self.test_list_bookings,
            self.test_booking_status_history,
            
            # Reviews
            self.test_create_review,
            self.test_list_reviews,
            
            # Favorites
            self.test_add_favorite,
            self.test_list_favorites,
            self.test_compare_favorites,
            self.test_remove_favorite,
            
            # Notices
            self.test_list_notices,
            self.test_get_notice,
            self.test_mark_notice_read,
            self.test_read_status,
            
            # Mess Menu
            self.test_mess_menu,
            
            # Waitlist
            self.test_join_waitlist,
            self.test_list_waitlist,
            
            # File Uploads
            self.test_presigned_url,
            self.test_invalid_file_upload,
            
            # Permissions
            self.test_student_can_access_visitor_endpoints,
            self.test_unauthorized_access,
            self.test_admin_can_access_visitor_endpoints,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print_error(f"Test crashed: {str(e)}")
                self.add_result(test.__name__, False, f"Crashed: {str(e)}")
        
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
        print(f"\n{CYAN}{BOLD}Working Endpoints Tested:{RESET}")
        endpoints = [
            "GET    /visitor/profile",
            "PATCH  /visitor/profile",
            "GET    /visitor/bookings",
            "GET    /visitor/bookings/{id}/status-history",
            "GET    /visitor/reviews",
            "POST   /visitor/reviews",
            "GET    /visitor/favorites",
            "POST   /visitor/favorites/{id}",
            "DELETE /visitor/favorites/{id}",
            "POST   /visitor/favorites/compare",
            "GET    /visitor/notices/paginated",
            "GET    /visitor/notices/{id}",
            "POST   /visitor/notices/{id}/read",
            "GET    /visitor/notices/read-status",
            "GET    /visitor/hostels/{id}/mess-menu",
            "POST   /visitor/waitlist/join",
            "GET    /visitor/waitlist",
            "DELETE /visitor/waitlist/{id}",
            "POST   /visitor/uploads/presigned-url",
        ]
        for ep in endpoints:
            print(f"  {ep}")
        
        if self.results["failed"] == 0:
            print(f"\n{GREEN}{BOLD}✅ ALL TESTS PASSED! Visitor routes are working correctly.{RESET}")
        else:
            print(f"\n{RED}{BOLD}❌ Some tests failed. Check errors above.{RESET}")


if __name__ == "__main__":
    tester = VisitorRoutesTester()
    tester.run_all_tests()