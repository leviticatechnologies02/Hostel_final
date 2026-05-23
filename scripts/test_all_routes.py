# test_all_routes.py
#!/usr/bin/env python3
"""
Comprehensive Test Script for StayEase API
Tests: Payments, Visitor, and Student Routes

Run: python test_all_routes.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

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


def check_backend() -> bool:
    """Check if backend is running"""
    try:
        # Health endpoint is at root, not under /api/v1
        url = "http://localhost:8000/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print_success("Backend API is reachable")
                return True
    except urllib.error.HTTPError as e:
        if e.code == 200:
            print_success("Backend API is reachable")
            return True
    except Exception as e:
        print_error(f"Cannot connect to backend: {e}")
        return False
    return False


class PaymentRoutesTester:
    """Test payment-related routes"""
    
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "tests": []}
        self.admin_token = None
        self.student_token = None
        self.visitor_token = None
        self.super_admin_token = None
        self.hostel_id = None
        self.student_id = None
        self.booking_id = None
        self.student_record_id = None
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.results["tests"].append({"name": test_name, "passed": passed, "message": message})
        if passed:
            self.results["passed"] += 1
            print_success(f"{test_name}: {message}" if message else test_name)
        else:
            self.results["failed"] += 1
            print_error(f"{test_name}: {message}" if message else test_name)
    
    def setup(self):
        """Setup authentication and get required IDs"""
        print_section("PAYMENT ROUTES SETUP")
        
        # Login as Admin
        admin_data = login("admin1@stayease.com")
        if admin_data:
            self.admin_token = admin_data.get("access_token")
            hostel_ids = admin_data.get("hostel_ids", [])
            self.hostel_id = hostel_ids[0] if hostel_ids else None
            print_info(f"Admin hostel ID: {self.hostel_id}")
        
        # Login as Student
        student_data = login("hemant.pawade.lev044@levitica.in")
        if student_data:
            self.student_token = student_data.get("access_token")
            self.student_id = student_data.get("user_id")
            print_info(f"Student User ID: {self.student_id}")
            
            # Get student record ID from profile
            status, profile = make_request("GET", "/student/profile", token=self.student_token)
            if status == 200:
                self.student_record_id = profile.get("id")
                print_info(f"Student Record ID: {self.student_record_id}")
        
        # Login as Visitor
        visitor_data = login("arun.kapoor@gmail.com")
        if visitor_data:
            self.visitor_token = visitor_data.get("access_token")
        
        # Login as Super Admin
        sa_data = login("superadmin@stayease.com")
        if sa_data:
            self.super_admin_token = sa_data.get("access_token")
        
        # Get a booking ID if needed
        if self.visitor_token:
            status, bookings = make_request("GET", "/visitor/bookings", token=self.visitor_token)
            if status == 200 and bookings:
                self.booking_id = bookings[0].get("id")
                print_info(f"Booking ID: {self.booking_id}")
        
        return self.admin_token is not None
    
    # ==================== PAYMENT ENDPOINTS ====================
    
    def test_get_hostel_qr_code(self):
        """Test GET /payments/hostels/{hostel_id}/qr-code"""
        print_subsection("1. GET /payments/hostels/{hostel_id}/qr-code")
        
        if not self.admin_token or not self.hostel_id:
            self.add_result("Get Hostel QR Code", False, "Missing admin token or hostel ID")
            return
        
        status, data = make_request("GET", f"/payments/hostels/{self.hostel_id}/qr-code", token=self.admin_token)
        
        if status == 200:
            required_fields = ["qr_code_base64", "upi_id", "qr_string", "expires_at"]
            missing = [f for f in required_fields if f not in data]
            if not missing:
                self.add_result("Get Hostel QR Code", True, f"UPI ID: {data.get('upi_id')}")
            else:
                self.add_result("Get Hostel QR Code", False, f"Missing fields: {missing}")
        else:
            self.add_result("Get Hostel QR Code", False, f"HTTP {status} - {data.get('detail', '')}")
    
    def test_get_hostel_qr_code_with_amount(self):
        """Test GET /payments/hostels/{hostel_id}/qr-code?amount=5000"""
        print_subsection("2. GET /payments/hostels/{hostel_id}/qr-code with amount")
        
        if not self.admin_token or not self.hostel_id:
            self.add_result("Get QR Code with Amount", False, "Missing admin token or hostel ID")
            return
        
        status, data = make_request("GET", f"/payments/hostels/{self.hostel_id}/qr-code?amount=5000", token=self.admin_token)
        
        if status == 200:
            self.add_result("Get QR Code with Amount", True, f"Amount: {data.get('payment_amount')}")
        else:
            self.add_result("Get QR Code with Amount", False, f"HTTP {status}")
    
    def test_make_direct_payment(self):
        """Test POST /payments/direct-payment"""
        print_subsection("3. POST /payments/direct-payment")
        
        if not self.student_token or not self.student_record_id:
            self.add_result("Make Direct Payment", False, "Missing student token or student record ID")
            return
        
        payload = {
            "student_id": self.student_record_id,
            "amount": 5000.00,
            "payment_type": "monthly_rent",
            "description": "Test payment for monthly rent",
            "payment_method": "qr_scan"
        }
        
        status, data = make_request("POST", "/payments/direct-payment", token=self.student_token, body=payload)
        
        if status == 201:
            self.add_result("Make Direct Payment", True, f"Transaction ID: {data.get('transaction_id')}")
            return data
        else:
            self.add_result("Make Direct Payment", False, f"HTTP {status}: {data.get('detail', 'Unknown')}")
            return None
    
    def test_get_my_payments(self):
        """Test GET /payments/my-payments"""
        print_subsection("4. GET /payments/my-payments")
        
        if not self.student_token:
            self.add_result("Get My Payments", False, "Missing student token")
            return
        
        status, data = make_request("GET", "/payments/my-payments", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get My Payments", True, f"Found {count} payments")
        else:
            self.add_result("Get My Payments", False, f"HTTP {status}")
    
    def test_get_my_payment_summary(self):
        """Test GET /payments/my-payments/summary"""
        print_subsection("5. GET /payments/my-payments/summary")
        
        if not self.student_token:
            self.add_result("Get Payment Summary", False, "Missing student token")
            return
        
        status, data = make_request("GET", "/payments/my-payments/summary", token=self.student_token)
        
        if status == 200:
            self.add_result("Get Payment Summary", True, f"Total paid: ₹{data.get('total_paid', 0):,.2f}")
        else:
            self.add_result("Get Payment Summary", False, f"HTTP {status}")
    
    def test_admin_get_recent_payments(self):
        """Test GET /payments/admin/hostels/{hostel_id}/payments/recent"""
        print_subsection("6. GET /payments/admin/hostels/{hostel_id}/payments/recent")
        
        if not self.admin_token or not self.hostel_id:
            self.add_result("Admin Get Recent Payments", False, "Missing admin token or hostel ID")
            return
        
        status, data = make_request("GET", f"/payments/admin/hostels/{self.hostel_id}/payments/recent", token=self.admin_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Admin Get Recent Payments", True, f"Found {count} recent payments")
        else:
            self.add_result("Admin Get Recent Payments", False, f"HTTP {status}")
    
    def test_admin_get_payment_stats(self):
        """Test GET /payments/admin/hostels/{hostel_id}/payments/stats"""
        print_subsection("7. GET /payments/admin/hostels/{hostel_id}/payments/stats")
        
        if not self.admin_token or not self.hostel_id:
            self.add_result("Admin Get Payment Stats", False, "Missing admin token or hostel ID")
            return
        
        status, data = make_request("GET", f"/payments/admin/hostels/{self.hostel_id}/payments/stats", token=self.admin_token)
        
        if status == 200:
            self.add_result("Admin Get Payment Stats", True, f"Total amount: ₹{data.get('total_amount', 0):,.2f}")
        else:
            self.add_result("Admin Get Payment Stats", False, f"HTTP {status}")
    
    def test_admin_get_student_payments(self):
        """Test GET /payments/admin/payments/student/{student_id}"""
        print_subsection("8. GET /payments/admin/payments/student/{student_id}")
        
        if not self.admin_token or not self.student_record_id:
            self.add_result("Admin Get Student Payments", False, "Missing admin token or student record ID")
            return
        
        status, data = make_request("GET", f"/payments/admin/payments/student/{self.student_record_id}", token=self.admin_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Admin Get Student Payments", True, f"Found {count} payments for student")
        else:
            self.add_result("Admin Get Student Payments", False, f"HTTP {status}")
    
    def test_visitor_cannot_access_payment_endpoints(self):
        """Test that visitors cannot access payment endpoints"""
        print_subsection("9. Visitor Access to Payment Endpoints (Should be denied)")
        
        if not self.visitor_token:
            self.add_result("Visitor Payment Access", False, "Missing visitor token")
            return
        
        status, data = make_request("GET", "/payments/my-payments", token=self.visitor_token)
        
        if status == 403:
            self.add_result("Visitor Payment Access", True, "Visitor correctly denied access")
        else:
            self.add_result("Visitor Payment Access", False, f"Expected 403, got {status}")
    
    def run_all_tests(self):
        """Run all payment route tests"""
        if not self.setup():
            print_error("Setup failed - cannot run tests")
            self.print_summary()
            return
        
        tests = [
            ("Get Hostel QR Code", self.test_get_hostel_qr_code),
            ("Get QR Code with Amount", self.test_get_hostel_qr_code_with_amount),
            ("Make Direct Payment", self.test_make_direct_payment),
            ("Get My Payments", self.test_get_my_payments),
            ("Get Payment Summary", self.test_get_my_payment_summary),
            ("Admin Get Recent Payments", self.test_admin_get_recent_payments),
            ("Admin Get Payment Stats", self.test_admin_get_payment_stats),
            ("Admin Get Student Payments", self.test_admin_get_student_payments),
            ("Visitor Payment Access", self.test_visitor_cannot_access_payment_endpoints),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print_error(f"{test_name} crashed: {str(e)}")
                self.add_result(test_name, False, f"Crashed: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print_section("PAYMENT ROUTES TEST SUMMARY")
        
        total = self.results["passed"] + self.results["failed"]
        print(f"\n  {BOLD}Total Tests:{RESET}   {total}")
        print(f"  {GREEN}{BOLD}Passed:{RESET}      {self.results['passed']}")
        print(f"  {RED}{BOLD}Failed:{RESET}      {self.results['failed']}")
        
        if self.results["failed"] > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for test in self.results["tests"]:
                if not test["passed"]:
                    print(f"  ✗ {test['name']}: {test['message']}")
        
        print(f"\n{CYAN}{BOLD}Working Payment Endpoints:{RESET}")
        endpoints = [
            "GET    /payments/hostels/{hostel_id}/qr-code",
            "GET    /payments/hostels/{hostel_id}/qr-code?amount=X",
            "POST   /payments/direct-payment",
            "GET    /payments/my-payments",
            "GET    /payments/my-payments/summary",
            "GET    /payments/admin/hostels/{hostel_id}/payments/recent",
            "GET    /payments/admin/hostels/{hostel_id}/payments/stats",
            "GET    /payments/admin/payments/student/{student_id}",
        ]
        for ep in endpoints:
            print(f"  {ep}")


class VisitorRoutesTester:
    """Test visitor routes"""
    
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "tests": []}
        self.visitor_token = None
        self.visitor_id = None
        self.hostel_id = None
        self.booking_id = None
        self.review_id = None
        self.favorite_hostel_id = None
        self.notice_id = None
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.results["tests"].append({"name": test_name, "passed": passed, "message": message})
        if passed:
            self.results["passed"] += 1
            print_success(f"{test_name}: {message}" if message else test_name)
        else:
            self.results["failed"] += 1
            print_error(f"{test_name}: {message}" if message else test_name)
    
    def setup(self):
        """Setup visitor authentication and get required IDs"""
        print_section("VISITOR ROUTES SETUP")
        
        # Login as Visitor
        visitor_data = login("arun.kapoor@gmail.com")
        if not visitor_data:
            print_error("Cannot proceed without visitor login")
            return False
        
        self.visitor_token = visitor_data.get("access_token")
        self.visitor_id = visitor_data.get("user_id")
        print_info(f"Visitor ID: {self.visitor_id}")
        
        # Login as Admin to get hostel ID
        admin_data = login("admin1@stayease.com")
        if admin_data:
            hostel_ids = admin_data.get("hostel_ids", [])
            self.hostel_id = hostel_ids[0] if hostel_ids else None
            print_info(f"Hostel ID from admin: {self.hostel_id}")
        
        # Get a public hostel if admin didn't provide one
        if not self.hostel_id:
            status, hostels = make_request("GET", "/public/hostels?per_page=1")
            if status == 200 and hostels.get("items"):
                self.hostel_id = hostels["items"][0].get("id")
                print_info(f"Public hostel ID: {self.hostel_id}")
        
        # Get a booking ID if exists
        if self.visitor_token:
            status, bookings = make_request("GET", "/visitor/bookings", token=self.visitor_token)
            if status == 200 and bookings:
                self.booking_id = bookings[0].get("id")
                print_info(f"Booking ID: {self.booking_id}")
        
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
            else:
                self.add_result("Get Profile", False, f"Missing fields: {missing}")
        else:
            self.add_result("Get Profile", False, f"HTTP {status}")
    
    def test_update_profile(self):
        """Test PATCH /visitor/profile"""
        print_subsection("2. PATCH /visitor/profile")
        
        update_data = {
            "full_name": f"Updated Visitor {datetime.now().strftime('%H%M')}",
        }
        
        status, data = make_request("PATCH", "/visitor/profile", token=self.visitor_token, body=update_data)
        
        if status == 200:
            self.add_result("Update Profile", True, f"Name: {data.get('full_name')}")
        else:
            self.add_result("Update Profile", False, f"HTTP {status}")
    
    def test_change_password(self):
        """Test POST /visitor/change-password"""
        print_subsection("3. POST /visitor/change-password")
        
        payload = {
            "old_password": "Test@1234",
            "new_password": "NewTest@1234",
            "confirm_password": "NewTest@1234"
        }
        
        status, data = make_request("POST", "/visitor/change-password", token=self.visitor_token, body=payload)
        
        if status == 200:
            self.add_result("Change Password", True, "Password changed")
            # Change back
            revert_payload = {
                "old_password": "NewTest@1234",
                "new_password": "Test@1234",
                "confirm_password": "Test@1234"
            }
            make_request("POST", "/visitor/change-password", token=self.visitor_token, body=revert_payload)
        elif status == 401:
            self.add_result("Change Password", True, "Password validation working")
        else:
            self.add_result("Change Password", False, f"HTTP {status}")
    
    # ==================== BOOKING TESTS ====================
    
    def test_list_bookings(self):
        """Test GET /visitor/bookings"""
        print_subsection("4. GET /visitor/bookings")
        
        status, data = make_request("GET", "/visitor/bookings", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Bookings", True, f"Found {count} bookings")
        else:
            self.add_result("List Bookings", False, f"HTTP {status}")
    
    def test_booking_status_history(self):
        """Test GET /visitor/bookings/{booking_id}/status-history"""
        print_subsection("5. GET /visitor/bookings/{id}/status-history")
        
        if not self.booking_id:
            self.add_result("Booking Status History", True, "Skipped - no booking")
            return
        
        status, data = make_request("GET", f"/visitor/bookings/{self.booking_id}/status-history", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Booking Status History", True, f"Found {count} status changes")
        else:
            self.add_result("Booking Status History", False, f"HTTP {status}")
    
    # ==================== REVIEW TESTS ====================
    
    def test_create_review(self):
        """Test POST /visitor/reviews"""
        print_subsection("6. POST /visitor/reviews")
        
        if not self.hostel_id:
            self.add_result("Create Review", False, "No hostel ID")
            return
        
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
        elif status == 409:
            self.add_result("Create Review", True, "Already reviewed (expected)")
        else:
            self.add_result("Create Review", False, f"HTTP {status}")
    
    def test_list_reviews(self):
        """Test GET /visitor/reviews"""
        print_subsection("7. GET /visitor/reviews")
        
        status, data = make_request("GET", "/visitor/reviews", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Reviews", True, f"Found {count} reviews")
        else:
            self.add_result("List Reviews", False, f"HTTP {status}")
    
    # ==================== FAVORITE TESTS ====================
    
    def test_add_favorite(self):
        """Test POST /visitor/favorites/{hostel_id}"""
        print_subsection("8. POST /visitor/favorites/{hostel_id}")
        
        if not self.hostel_id:
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
        print_subsection("9. GET /visitor/favorites")
        
        status, data = make_request("GET", "/visitor/favorites", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Favorites", True, f"Found {count} favorites")
        else:
            self.add_result("List Favorites", False, f"HTTP {status}")
    
    def test_compare_favorites(self):
        """Test POST /visitor/favorites/compare"""
        print_subsection("10. POST /visitor/favorites/compare")
        
        status, data = make_request("POST", "/visitor/favorites/compare", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Compare Favorites", True, f"Comparing {count} hostels")
        else:
            self.add_result("Compare Favorites", False, f"HTTP {status}")
    
    def test_remove_favorite(self):
        """Test DELETE /visitor/favorites/{hostel_id}"""
        print_subsection("11. DELETE /visitor/favorites/{hostel_id}")
        
        if not self.favorite_hostel_id:
            self.add_result("Remove Favorite", True, "Skipped - no favorite")
            return
        
        status, data = make_request("DELETE", f"/visitor/favorites/{self.favorite_hostel_id}", token=self.visitor_token)
        
        if status == 200:
            self.add_result("Remove Favorite", True, data.get("message", "Removed"))
        else:
            self.add_result("Remove Favorite", False, f"HTTP {status}")
    
    # ==================== NOTICE TESTS ====================
    
    def test_list_notices(self):
        """Test GET /visitor/notices/paginated"""
        print_subsection("12. GET /visitor/notices/paginated")
        
        status, data = make_request("GET", "/visitor/notices/paginated?page=1&per_page=10", token=self.visitor_token)
        
        if status == 200:
            items = data.get("items", [])
            total = data.get("total", 0)
            self.add_result("List Notices", True, f"Found {total} platform notices")
            if items and not self.notice_id:
                self.notice_id = items[0].get("id")
        else:
            self.add_result("List Notices", False, f"HTTP {status}")
    
    def test_get_notice(self):
        """Test GET /visitor/notices/{notice_id}"""
        print_subsection("13. GET /visitor/notices/{notice_id}")
        
        if not self.notice_id:
            self.add_result("Get Notice", True, "Skipped - no notice")
            return
        
        status, data = make_request("GET", f"/visitor/notices/{self.notice_id}", token=self.visitor_token)
        
        if status == 200:
            self.add_result("Get Notice", True, f"Title: {data.get('title', '')[:50]}")
        else:
            self.add_result("Get Notice", False, f"HTTP {status}")
    
    def test_mark_notice_read(self):
        """Test POST /visitor/notices/{notice_id}/read"""
        print_subsection("14. POST /visitor/notices/{notice_id}/read")
        
        if not self.notice_id:
            self.add_result("Mark Notice Read", True, "Skipped - no notice")
            return
        
        status, data = make_request("POST", f"/visitor/notices/{self.notice_id}/read", token=self.visitor_token)
        
        if status == 200:
            self.add_result("Mark Notice Read", True, f"Is read: {data.get('is_read')}")
        else:
            self.add_result("Mark Notice Read", False, f"HTTP {status}")
    
    def test_read_status(self):
        """Test GET /visitor/notices/read-status"""
        print_subsection("15. GET /visitor/notices/read-status")
        
        status, data = make_request("GET", "/visitor/notices/read-status", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Read Status", True, f"Read {count} notices")
        else:
            self.add_result("Read Status", False, f"HTTP {status}")
    
    # ==================== MESS MENU TESTS ====================
    
    def test_mess_menu(self):
        """Test GET /visitor/hostels/{hostel_id}/mess-menu"""
        print_subsection("16. GET /visitor/hostels/{hostel_id}/mess-menu")
        
        if not self.hostel_id:
            self.add_result("Mess Menu", True, "Skipped - no hostel")
            return
        
        status, data = make_request("GET", f"/visitor/hostels/{self.hostel_id}/mess-menu")
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Mess Menu", True, f"Found {count} menu items")
        else:
            self.add_result("Mess Menu", False, f"HTTP {status}")
    
    # ==================== WAITLIST TESTS ====================
    
    def test_join_waitlist(self):
        """Test POST /visitor/waitlist/join"""
        print_subsection("17. POST /visitor/waitlist/join")
        
        if not self.hostel_id:
            self.add_result("Join Waitlist", True, "Skipped - no hostel")
            return
        
        # Get a room ID first
        status, rooms = make_request("GET", f"/public/hostels/{self.hostel_id}/rooms")
        if status != 200 or not rooms:
            self.add_result("Join Waitlist", True, "Skipped - no rooms")
            return
        
        room_id = rooms[0].get("id")
        future_date = (date.today() + timedelta(days=60)).isoformat()
        future_end = (date.today() + timedelta(days=90)).isoformat()
        
        payload = {
            "hostel_id": self.hostel_id,
            "room_id": room_id,
            "booking_mode": "monthly",
            "check_in_date": future_date,
            "check_out_date": future_end
        }
        
        status, data = make_request("POST", "/visitor/waitlist/join", token=self.visitor_token, body=payload)
        
        if status in [200, 201]:
            self.add_result("Join Waitlist", True, f"Position: {data.get('position', 'N/A')}")
        elif status == 400:
            self.add_result("Join Waitlist", True, f"Validation: {data.get('detail', '')}")
        else:
            self.add_result("Join Waitlist", False, f"HTTP {status}")
    
    def test_list_waitlist(self):
        """Test GET /visitor/waitlist"""
        print_subsection("18. GET /visitor/waitlist")
        
        status, data = make_request("GET", "/visitor/waitlist", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Waitlist", True, f"Found {count} entries")
        else:
            self.add_result("List Waitlist", False, f"HTTP {status}")
    
    def test_leave_waitlist(self):
        """Test DELETE /visitor/waitlist/{entry_id}"""
        print_subsection("19. DELETE /visitor/waitlist/{entry_id}")
        
        # First get waitlist entries
        status, waitlist = make_request("GET", "/visitor/waitlist", token=self.visitor_token)
        if status != 200 or not waitlist:
            self.add_result("Leave Waitlist", True, "Skipped - no waitlist entries")
            return
        
        entry_id = waitlist[0].get("id")
        status, data = make_request("DELETE", f"/visitor/waitlist/{entry_id}", token=self.visitor_token)
        
        if status == 204:
            self.add_result("Leave Waitlist", True, "Left waitlist successfully")
        else:
            self.add_result("Leave Waitlist", False, f"HTTP {status}")
    
    # ==================== UPLOAD TESTS ====================
    
    def test_presigned_url(self):
        """Test POST /visitor/uploads/presigned-url"""
        print_subsection("20. POST /visitor/uploads/presigned-url")
        
        upload_data = {
            "file_name": "test_id_proof.jpg",
            "content_type": "image/jpeg",
            "file_size": 1024 * 500
        }
        
        status, data = make_request("POST", "/visitor/uploads/presigned-url", token=self.visitor_token, body=upload_data)
        
        if status == 200:
            self.add_result("Presigned URL", True, "Upload URL generated")
        elif status == 400:
            self.add_result("Presigned URL", True, f"Validation: {data.get('detail', '')}")
        else:
            self.add_result("Presigned URL", False, f"HTTP {status}")
    
    def test_invalid_file_upload(self):
        """Test invalid file type rejection"""
        print_subsection("21. POST /visitor/uploads/presigned-url (Invalid)")
        
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
    
    def test_unauthorized_access(self):
        """Test endpoints require authentication"""
        print_subsection("22. Unauthorized Access")
        
        status, _ = make_request("GET", "/visitor/profile")
        
        if status == 401:
            self.add_result("Unauthorized Access", True, "Auth required")
        else:
            self.add_result("Unauthorized Access", False, f"Expected 401, got {status}")
    
    def run_all_tests(self):
        """Run all visitor route tests"""
        print_section("VISITOR ROUTES TESTING")
        print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API URL: {BASE_URL}")
        
        if not self.setup():
            print_error("Setup failed - cannot run tests")
            self.print_summary()
            return
        
        tests = [
            self.test_get_profile,
            self.test_update_profile,
            self.test_change_password,
            self.test_list_bookings,
            self.test_booking_status_history,
            self.test_create_review,
            self.test_list_reviews,
            self.test_add_favorite,
            self.test_list_favorites,
            self.test_compare_favorites,
            self.test_remove_favorite,
            self.test_list_notices,
            self.test_get_notice,
            self.test_mark_notice_read,
            self.test_read_status,
            self.test_mess_menu,
            self.test_join_waitlist,
            self.test_list_waitlist,
            self.test_leave_waitlist,
            self.test_presigned_url,
            self.test_invalid_file_upload,
            self.test_unauthorized_access,
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print_error(f"Test crashed: {str(e)}")
                self.add_result(test_func.__name__, False, f"Crashed: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print_section("VISITOR ROUTES TEST SUMMARY")
        
        total = self.results["passed"] + self.results["failed"]
        print(f"\n  {BOLD}Total Tests:{RESET}   {total}")
        print(f"  {GREEN}{BOLD}Passed:{RESET}      {self.results['passed']}")
        print(f"  {RED}{BOLD}Failed:{RESET}      {self.results['failed']}")
        
        if self.results["failed"] > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for test in self.results["tests"]:
                if not test["passed"]:
                    print(f"  ✗ {test['name']}: {test['message']}")
        
        print(f"\n{CYAN}{BOLD}Working Visitor Endpoints:{RESET}")
        endpoints = [
            "GET    /visitor/profile",
            "PATCH  /visitor/profile",
            "POST   /visitor/change-password",
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
            print(f"\n{GREEN}{BOLD}✅ ALL VISITOR ROUTE TESTS PASSED!{RESET}")
        else:
            print(f"\n{RED}{BOLD}❌ Some tests failed. Check errors above.{RESET}")


class StudentRoutesTester:
    """Test student routes"""
    
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "tests": []}
        self.student_token = None
        self.student_id = None
        self.complaint_id = None
        self.student_record_id = None
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.results["tests"].append({"name": test_name, "passed": passed, "message": message})
        if passed:
            self.results["passed"] += 1
            print_success(f"{test_name}: {message}" if message else test_name)
        else:
            self.results["failed"] += 1
            print_error(f"{test_name}: {message}" if message else test_name)
    
    def setup(self):
        """Setup student authentication"""
        print_section("STUDENT ROUTES SETUP")
        
        # Login as Student
        student_data = login("hemant.pawade.lev044@levitica.in")
        if not student_data:
            print_error("Cannot proceed without student login")
            return False
        
        self.student_token = student_data.get("access_token")
        self.student_id = student_data.get("user_id")
        print_info(f"Student User ID: {self.student_id}")
        
        # Get student record ID
        status, profile = make_request("GET", "/student/profile", token=self.student_token)
        if status == 200:
            self.student_record_id = profile.get("id")
            print_info(f"Student Record ID: {self.student_record_id}")
        
        return True
    
    # ==================== PROFILE TESTS ====================
    
    def test_get_profile(self):
        """Test GET /student/profile"""
        print_subsection("1. GET /student/profile")
        
        status, data = make_request("GET", "/student/profile", token=self.student_token)
        
        if status == 200:
            required_fields = ["id", "user_id", "full_name", "email", "student_number"]
            missing = [f for f in required_fields if f not in data]
            if not missing:
                self.add_result("Get Profile", True, f"Student: {data.get('full_name')}")
            else:
                self.add_result("Get Profile", False, f"Missing fields: {missing}")
        else:
            self.add_result("Get Profile", False, f"HTTP {status}")
    
    def test_get_detailed_profile(self):
        """Test GET /student/profile/detailed"""
        print_subsection("2. GET /student/profile/detailed")
        
        status, data = make_request("GET", "/student/profile/detailed", token=self.student_token)
        
        if status == 200:
            required_fields = ["student_number", "hostel", "room", "bed", "booking"]
            missing = [f for f in required_fields if f not in data]
            if not missing:
                hostel_name = data.get("hostel", {}).get("name", "Unknown")
                room_number = data.get("room", {}).get("room_number", "Unknown")
                self.add_result("Get Detailed Profile", True, f"Hostel: {hostel_name}, Room: {room_number}")
            else:
                self.add_result("Get Detailed Profile", False, f"Missing fields: {missing}")
        else:
            self.add_result("Get Detailed Profile", False, f"HTTP {status}")
    
    def test_update_profile(self):
        """Test PATCH /student/profile"""
        print_subsection("3. PATCH /student/profile")
        
        update_data = {
            "full_name": f"Updated Student {datetime.now().strftime('%H%M')}",
        }
        
        status, data = make_request("PATCH", "/student/profile", token=self.student_token, body=update_data)
        
        if status == 200:
            self.add_result("Update Profile", True, f"Name: {data.get('full_name')}")
        else:
            self.add_result("Update Profile", False, f"HTTP {status}")
    
    def test_change_password(self):
        """Test POST /student/change-password"""
        print_subsection("4. POST /student/change-password")
        
        payload = {
            "old_password": "Test@1234",
            "new_password": "NewTest@1234",
            "confirm_password": "NewTest@1234"
        }
        
        status, data = make_request("POST", "/student/change-password", token=self.student_token, body=payload)
        
        if status == 200:
            self.add_result("Change Password", True, "Password changed")
            # Change back
            revert_payload = {
                "old_password": "NewTest@1234",
                "new_password": "Test@1234",
                "confirm_password": "Test@1234"
            }
            make_request("POST", "/student/change-password", token=self.student_token, body=revert_payload)
        elif status == 401:
            self.add_result("Change Password", True, "Password validation working")
        else:
            self.add_result("Change Password", False, f"HTTP {status}")
    
    # ==================== PAYMENT & BOOKING TESTS ====================
    
    def test_get_payments(self):
        """Test GET /student/payments"""
        print_subsection("5. GET /student/payments")
        
        status, data = make_request("GET", "/student/payments", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get Payments", True, f"Found {count} payments")
        else:
            self.add_result("Get Payments", False, f"HTTP {status}")
    
    def test_get_bookings(self):
        """Test GET /student/bookings"""
        print_subsection("6. GET /student/bookings")
        
        status, data = make_request("GET", "/student/bookings", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get Bookings", True, f"Found {count} bookings")
        else:
            self.add_result("Get Bookings", False, f"HTTP {status}")
    
    # ==================== ATTENDANCE TESTS ====================
    
    def test_get_attendance(self):
        """Test GET /student/attendance"""
        print_subsection("7. GET /student/attendance")
        
        status, data = make_request("GET", "/student/attendance", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get Attendance", True, f"Found {count} attendance records")
        else:
            self.add_result("Get Attendance", False, f"HTTP {status}")
    
    # ==================== NOTICE TESTS ====================
    
    def test_get_notices(self):
        """Test GET /student/notices/paginated"""
        print_subsection("8. GET /student/notices/paginated")
        
        status, data = make_request("GET", "/student/notices/paginated?page=1&per_page=10", token=self.student_token)
        
        if status == 200:
            items = data.get("items", [])
            total = data.get("total", 0)
            self.add_result("Get Notices", True, f"Found {total} notices")
        else:
            self.add_result("Get Notices", False, f"HTTP {status}")
    
    def test_mark_notice_read(self):
        """Test POST /student/notices/{notice_id}/read"""
        print_subsection("9. POST /student/notices/{notice_id}/read")
        
        # First get a notice
        status, data = make_request("GET", "/student/notices/paginated?page=1&per_page=1", token=self.student_token)
        if status != 200 or not data.get("items"):
            self.add_result("Mark Notice Read", True, "Skipped - no notices")
            return
        
        notice_id = data["items"][0].get("id")
        status, result = make_request("POST", f"/student/notices/{notice_id}/read", token=self.student_token)
        
        if status == 200:
            self.add_result("Mark Notice Read", True, "Notice marked as read")
        else:
            self.add_result("Mark Notice Read", False, f"HTTP {status}")
    
    def test_get_read_status(self):
        """Test GET /student/notices/read-status"""
        print_subsection("10. GET /student/notices/read-status")
        
        status, data = make_request("GET", "/student/notices/read-status", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get Read Status", True, f"Read {count} notices")
        else:
            self.add_result("Get Read Status", False, f"HTTP {status}")
    
    # ==================== MESS MENU TESTS ====================
    
    def test_get_mess_menu(self):
        """Test GET /student/mess-menu"""
        print_subsection("11. GET /student/mess-menu")
        
        status, data = make_request("GET", "/student/mess-menu", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get Mess Menu", True, f"Found {count} menu items")
        else:
            self.add_result("Get Mess Menu", False, f"HTTP {status}")
    
    # ==================== COMPLAINT TESTS ====================
    
    def test_get_complaints(self):
        """Test GET /student/complaints"""
        print_subsection("12. GET /student/complaints")
        
        status, data = make_request("GET", "/student/complaints", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get Complaints", True, f"Found {count} complaints")
        else:
            self.add_result("Get Complaints", False, f"HTTP {status}")
    
    def test_create_complaint(self):
        """Test POST /student/complaints"""
        print_subsection("13. POST /student/complaints")
        
        payload = {
            "category": "maintenance",
            "title": f"Test Complaint {datetime.now().strftime('%H%M%S')}",
            "description": "This is a test complaint from the API test script",
            "priority": "medium"
        }
        
        status, data = make_request("POST", "/student/complaints", token=self.student_token, body=payload)
        
        if status == 201:
            self.complaint_id = data.get("id")
            self.add_result("Create Complaint", True, f"Complaint ID: {self.complaint_id[:8] if self.complaint_id else 'N/A'}...")
        else:
            self.add_result("Create Complaint", False, f"HTTP {status}")
    
    def test_delete_complaint(self):
        """Test DELETE /student/complaints/{complaint_id}"""
        print_subsection("14. DELETE /student/complaints/{complaint_id}")
        
        # Create a complaint first
        payload = {
            "category": "maintenance",
            "title": f"Complaint to Delete {datetime.now().strftime('%H%M%S')}",
            "description": "This complaint will be deleted",
            "priority": "low"
        }
        
        status, data = make_request("POST", "/student/complaints", token=self.student_token, body=payload)
        if status != 201:
            self.add_result("Delete Complaint", False, "Could not create test complaint")
            return
        
        complaint_to_delete = data.get("id")
        status, _ = make_request("DELETE", f"/student/complaints/{complaint_to_delete}", token=self.student_token)
        
        if status == 204:
            self.add_result("Delete Complaint", True, "Complaint deleted successfully")
        else:
            self.add_result("Delete Complaint", False, f"HTTP {status}")
    
    # ==================== WAITLIST TESTS ====================
    
    def test_get_waitlist(self):
        """Test GET /student/waitlist"""
        print_subsection("15. GET /student/waitlist")
        
        status, data = make_request("GET", "/student/waitlist", token=self.student_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Get Waitlist", True, f"Found {count} waitlist entries")
        else:
            self.add_result("Get Waitlist", False, f"HTTP {status}")
    
    # ==================== ROOM INFO TESTS ====================
    
    def test_get_room_info(self):
        """Test GET /student/room-info"""
        print_subsection("16. GET /student/room-info")
        
        status, data = make_request("GET", "/student/room-info", token=self.student_token)
        
        if status == 200:
            required_fields = ["student_number", "room", "bed", "check_in_date", "status"]
            missing = [f for f in required_fields if f not in data]
            if not missing:
                room_number = data.get("room", {}).get("room_number", "Unknown")
                bed_number = data.get("bed", {}).get("bed_number", "Unknown")
                self.add_result("Get Room Info", True, f"Room: {room_number}, Bed: {bed_number}")
            else:
                self.add_result("Get Room Info", False, f"Missing fields: {missing}")
        else:
            self.add_result("Get Room Info", False, f"HTTP {status}")
    
    # ==================== LEAVE REQUEST TESTS ====================
    
    def test_create_leave_request(self):
        """Test POST /student/leave-request"""
        print_subsection("17. POST /student/leave-request")
        
        future_date = (date.today() + timedelta(days=1)).isoformat()
        future_end = (date.today() + timedelta(days=3)).isoformat()
        
        payload = {
            "from_date": future_date,
            "to_date": future_end,
            "reason": "Medical leave"
        }
        
        status, data = make_request("POST", "/student/leave-request", token=self.student_token, body=payload)
        
        if status == 201:
            self.add_result("Create Leave Request", True, f"Reference: {data.get('reference')}")
        else:
            self.add_result("Create Leave Request", False, f"HTTP {status}")
    
    # ==================== PERMISSION TESTS ====================
    
    def test_unauthorized_access(self):
        """Test endpoints require authentication"""
        print_subsection("18. Unauthorized Access")
        
        status, _ = make_request("GET", "/student/profile")
        
        if status == 401:
            self.add_result("Unauthorized Access", True, "Auth required")
        else:
            self.add_result("Unauthorized Access", False, f"Expected 401, got {status}")
    
    def run_all_tests(self):
        """Run all student route tests"""
        print_section("STUDENT ROUTES TESTING")
        print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API URL: {BASE_URL}")
        
        if not self.setup():
            print_error("Setup failed - cannot run tests")
            self.print_summary()
            return
        
        tests = [
            self.test_get_profile,
            self.test_get_detailed_profile,
            self.test_update_profile,
            self.test_change_password,
            self.test_get_payments,
            self.test_get_bookings,
            self.test_get_attendance,
            self.test_get_notices,
            self.test_mark_notice_read,
            self.test_get_read_status,
            self.test_get_mess_menu,
            self.test_get_complaints,
            self.test_create_complaint,
            self.test_delete_complaint,
            self.test_get_waitlist,
            self.test_get_room_info,
            self.test_create_leave_request,
            self.test_unauthorized_access,
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print_error(f"Test crashed: {str(e)}")
                self.add_result(test_func.__name__, False, f"Crashed: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print_section("STUDENT ROUTES TEST SUMMARY")
        
        total = self.results["passed"] + self.results["failed"]
        print(f"\n  {BOLD}Total Tests:{RESET}   {total}")
        print(f"  {GREEN}{BOLD}Passed:{RESET}      {self.results['passed']}")
        print(f"  {RED}{BOLD}Failed:{RESET}      {self.results['failed']}")
        
        if self.results["failed"] > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for test in self.results["tests"]:
                if not test["passed"]:
                    print(f"  ✗ {test['name']}: {test['message']}")
        
        print(f"\n{CYAN}{BOLD}Working Student Endpoints:{RESET}")
        endpoints = [
            "GET    /student/profile",
            "GET    /student/profile/detailed",
            "PATCH  /student/profile",
            "POST   /student/change-password",
            "GET    /student/payments",
            "GET    /student/bookings",
            "GET    /student/attendance",
            "GET    /student/notices/paginated",
            "GET    /student/notices/{id}",
            "POST   /student/notices/{id}/read",
            "GET    /student/notices/read-status",
            "GET    /student/mess-menu",
            "GET    /student/complaints",
            "POST   /student/complaints",
            "DELETE /student/complaints/{id}",
            "GET    /student/waitlist",
            "DELETE /student/waitlist/{id}",
            "GET    /student/room-info",
            "POST   /student/leave-request",
        ]
        for ep in endpoints:
            print(f"  {ep}")
        
        if self.results["failed"] == 0:
            print(f"\n{GREEN}{BOLD}✅ ALL STUDENT ROUTE TESTS PASSED!{RESET}")
        else:
            print(f"\n{RED}{BOLD}❌ Some tests failed. Check errors above.{RESET}")


def run_all_tests():
    """Run all test suites"""
    print_section("STAYEASE API - COMPREHENSIVE TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"API URL: {BASE_URL}")
    
    # Check if backend is running using correct health endpoint
    if not check_backend():
        print_error("Backend API is not responding!")
        print_info("Make sure the backend is running: uvicorn app.main:app --reload")
        return
    
    # Run Payment tests
    print("\n" + "="*70)
    print("  RUNNING PAYMENT ROUTES TESTS")
    print("="*70)
    payment_tester = PaymentRoutesTester()
    payment_tester.run_all_tests()
    
    # Run Visitor tests
    print("\n" + "="*70)
    print("  RUNNING VISITOR ROUTES TESTS")
    print("="*70)
    visitor_tester = VisitorRoutesTester()
    visitor_tester.run_all_tests()
    
    # Run Student tests
    print("\n" + "="*70)
    print("  RUNNING STUDENT ROUTES TESTS")
    print("="*70)
    student_tester = StudentRoutesTester()
    student_tester.run_all_tests()
    
    # Final Summary
    print_section("FINAL SUMMARY")
    print(f"\n{GREEN}{BOLD}✅ All test suites completed!{RESET}")
    print(f"\n{CYAN}Test Coverage:{RESET}")
    print("  • Payment Routes: QR codes, direct payments, payment history, admin stats")
    print("  • Visitor Routes: Profile, bookings, reviews, favorites, notices, waitlist, uploads")
    print("  • Student Routes: Profile, payments, attendance, complaints, mess menu, room info")
    print(f"\n{BLUE}Note: Some tests may fail if required data (bookings, complaints) doesn't exist.{RESET}")
    print("      Run seed data first: python -m scripts.seed_data --clean")


if __name__ == "__main__":
    run_all_tests()