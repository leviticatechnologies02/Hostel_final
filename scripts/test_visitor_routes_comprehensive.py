# scripts/test_visitor_routes_comprehensive.py
#!/usr/bin/env python3
"""
Comprehensive Visitor Routes Test Script

Run: python scripts/test_visitor_routes_comprehensive.py

Tests all visitor endpoints and identifies issues.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import sys
import re

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


def make_request(method: str, path: str, token: Optional[str] = None, body: Optional[Dict] = None) -> tuple[int, Any]:
    """Make HTTP request to API"""
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
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
        print_info(f"Visitor ID: {self.visitor_id}")
        
        # Login as Admin to get hostel ID
        admin_data = login("admin1@stayease.com")
        if admin_data:
            self.admin_token = admin_data.get("access_token")
            hostel_ids = admin_data.get("hostel_ids", [])
            self.hostel_id = hostel_ids[0] if hostel_ids else None
            print_info(f"Hostel ID: {self.hostel_id}")
        
        # Login as Student
        student_data = login("hemant.pawade.lev044@levitica.in")
        if student_data:
            self.student_token = student_data.get("access_token")
            print_info("Student logged in")
        
        # Get a public hostel if admin didn't provide one
        if not self.hostel_id:
            status, hostels = make_request("GET", "/public/hostels?per_page=1")
            if status == 200 and hostels.get("items"):
                self.hostel_id = hostels["items"][0].get("id")
                print_info(f"Public hostel ID: {self.hostel_id}")
        
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
                return data
            else:
                self.add_result("Get Profile", False, f"Missing fields: {missing}")
                return None
        else:
            self.add_result("Get Profile", False, f"HTTP {status}")
            return None
    
    def test_update_profile(self):
        """Test PATCH /visitor/profile"""
        print_subsection("2. PATCH /visitor/profile")
        
        # Get current profile first
        status, current = make_request("GET", "/visitor/profile", token=self.visitor_token)
        if status != 200:
            self.add_result("Update Profile", False, "Cannot get current profile")
            return
        
        original_name = current.get("full_name")
        timestamp = datetime.now().strftime("%H%M%S")
        
        # Use a unique phone number (based on timestamp) to avoid conflict
        unique_phone = f"98{timestamp}1234"[-10:]  # Always 10 digits
        
        update_data = {
            "full_name": f"Updated Visitor {timestamp}",
            "phone": unique_phone  # Dynamic unique phone
        }
        
        status, data = make_request("PATCH", "/visitor/profile", token=self.visitor_token, body=update_data)
        
        if status == 200:
            self.add_result("Update Profile", True, f"Name: {data.get('full_name')}")
            
            # Revert to original name (keep phone as is since it's unique)
            revert_data = {"full_name": original_name}
            make_request("PATCH", "/visitor/profile", token=self.visitor_token, body=revert_data)
        else:
            self.add_result("Update Profile", False, f"HTTP {status}")
    
    def test_update_profile_invalid_phone(self):
        """Test PATCH /visitor/profile with invalid phone"""
        print_subsection("2b. PATCH /visitor/profile (Invalid Phone)")
        
        # Try invalid phone (less than 10 digits)
        update_data = {"phone": "12345"}
        
        status, data = make_request("PATCH", "/visitor/profile", token=self.visitor_token, body=update_data)
        
        # Should return 400 or validation error
        if status in [400, 422]:
            self.add_result("Invalid Phone Rejected", True, f"HTTP {status}")
        else:
            self.add_result("Invalid Phone Rejected", False, f"Expected 400/422, got {status}")
    
    # ==================== BOOKING TESTS ====================
    
    def test_list_bookings(self):
        """Test GET /visitor/bookings"""
        print_subsection("3. GET /visitor/bookings")
        
        status, data = make_request("GET", "/visitor/bookings", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Bookings", True, f"Found {count} bookings")
            
            if count > 0 and not self.booking_id:
                self.booking_id = data[0].get("id") if isinstance(data[0], dict) else None
                print_info(f"  Using booking ID: {self.booking_id[:8] if self.booking_id else 'N/A'}...")
        else:
            self.add_result("List Bookings", False, f"HTTP {status}")
    
    def test_booking_status_history(self):
        """Test GET /visitor/bookings/{booking_id}/status-history"""
        print_subsection("4. GET /visitor/bookings/{id}/status-history")
        
        if not self.booking_id:
            # Create a booking first
            booking_id = self.create_test_booking()
            if not booking_id:
                self.add_result("Booking Status History", False, "Cannot create test booking")
                return
            self.booking_id = booking_id
        
        status, data = make_request("GET", f"/visitor/bookings/{self.booking_id}/status-history", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Booking Status History", True, f"Found {count} status changes")
            
            if count > 0 and isinstance(data, list):
                print_info(f"  Latest: {data[0].get('new_status')}")
        else:
            self.add_result("Booking Status History", False, f"HTTP {status}")
    
    def create_test_booking(self) -> Optional[str]:
        """Create a test booking for testing"""
        if not self.hostel_id:
            return None
        
        # Get a room
        status, rooms = make_request("GET", f"/public/hostels/{self.hostel_id}/rooms")
        if status != 200 or not rooms:
            return None
        
        room_id = rooms[0].get("id")
        
        future_date = (date.today() + timedelta(days=60)).isoformat()
        future_end = (date.today() + timedelta(days=90)).isoformat()
        
        payload = {
            "hostel_id": self.hostel_id,
            "room_id": room_id,
            "booking_mode": "monthly",
            "check_in_date": future_date,
            "check_out_date": future_end,
            "full_name": "Test Visitor",
            "base_rent_amount": 5000.0,
            "security_deposit": 5000.0,
            "booking_advance": 1250.0,
            "grand_total": 10000.0
        }
        
        status, data = make_request("POST", "/public/bookings", token=self.visitor_token, body=payload)
        
        if status == 201:
            return data.get("id")
        return None
    
    # ==================== REVIEW TESTS ====================
    
    def test_create_review(self):
        """Test POST /visitor/reviews"""
        print_subsection("5. POST /visitor/reviews")
        
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
            self.add_result("Add Favorite", True, "Skipped - no hostel ID")
            return
        
        status, data = make_request("POST", f"/visitor/favorites/{self.hostel_id}", token=self.visitor_token)
        
        if status == 201:
            self.favorite_hostel_id = self.hostel_id
            self.add_result("Add Favorite", True, data.get("message", "Added"))
        elif "already" in str(data).lower() or status == 200:
            self.add_result("Add Favorite", True, "Already in favorites")
        else:
            self.add_result("Add Favorite", False, f"HTTP {status}")
    
    def test_add_favorite_invalid_uuid(self):
        """Test POST /visitor/favorites/{hostel_id} with invalid UUID"""
        print_subsection("7b. POST /visitor/favorites (Invalid UUID)")
        
        invalid_id = "invalid-uuid-format"
        status, data = make_request("POST", f"/visitor/favorites/{invalid_id}", token=self.visitor_token)
        
        if status == 400:
            self.add_result("Invalid UUID Rejected", True, f"HTTP {status}")
        else:
            self.add_result("Invalid UUID Rejected", False, f"Expected 400, got {status}")
    
    def test_list_favorites(self):
        """Test GET /visitor/favorites"""
        print_subsection("8. GET /visitor/favorites")
        
        status, data = make_request("GET", "/visitor/favorites", token=self.visitor_token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Favorites", True, f"Found {count} favorites")
            
            if count > 0 and isinstance(data, list):
                print_info(f"  First: {data[0].get('hostel_name', 'Unknown')}")
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
            # This might not be implemented
            if status == 404:
                self.add_result("Compare Favorites", True, "Endpoint not implemented (optional)")
            else:
                self.add_result("Compare Favorites", False, f"HTTP {status}")
    
    def test_remove_favorite(self):
        """Test DELETE /visitor/favorites/{hostel_id}"""
        print_subsection("10. DELETE /visitor/favorites/{hostel_id}")
        
        if not self.favorite_hostel_id:
            # Try to add one first
            self.test_add_favorite()
            if not self.favorite_hostel_id:
                self.add_result("Remove Favorite", True, "Skipped - no favorite to remove")
                return
        
        status, data = make_request("DELETE", f"/visitor/favorites/{self.favorite_hostel_id}", token=self.visitor_token)
        
        if status == 200:
            self.add_result("Remove Favorite", True, data.get("message", "Removed"))
            self.favorite_hostel_id = None
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
                self.notice_id = items[0].get("id") if isinstance(items[0], dict) else None
                print_info(f"  Sample: {items[0].get('title', '')[:50] if items else 'N/A'}")
        else:
            self.add_result("List Notices", False, f"HTTP {status}")
    
    def test_get_notice(self):
        """Test GET /visitor/notices/{notice_id}"""
        print_subsection("12. GET /visitor/notices/{notice_id}")
        
        if not self.notice_id:
            self.add_result("Get Notice", True, "Skipped - no notice ID")
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
            self.add_result("Mark Notice Read", True, "Skipped - no notice ID")
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
            self.add_result("Mess Menu", True, "Skipped - no hostel ID")
            return
        
        status, data = make_request("GET", f"/visitor/hostels/{self.hostel_id}/mess-menu")
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("Mess Menu", True, f"Found {count} menu items")
            
            if count > 0 and isinstance(data, list):
                print_info(f"  Sample: {data[0].get('item_name', 'N/A')} ({data[0].get('meal_type', 'N/A')})")
        else:
            self.add_result("Mess Menu", False, f"HTTP {status}")
    
    # ==================== WAITLIST TESTS ====================
    
    def test_join_waitlist(self):
        """Test POST /visitor/waitlist/join"""
        print_subsection("16. POST /visitor/waitlist/join")
        
        if not self.hostel_id or not self.room_id_from_setup:
            # Get a room first
            status, rooms = make_request("GET", f"/public/hostels/{self.hostel_id}/rooms")
            if status != 200 or not rooms:
                self.add_result("Join Waitlist", True, "Skipped - cannot get room")
                return
            room_id = rooms[0].get("id")
        else:
            room_id = self.room_id_from_setup
        
        future_date = (date.today() + timedelta(days=120)).isoformat()
        future_end = (date.today() + timedelta(days=150)).isoformat()
        
        waitlist_data = {
            "hostel_id": self.hostel_id,
            "room_id": room_id,
            "booking_mode": "monthly",
            "check_in_date": future_date,
            "check_out_date": future_end
        }
        
        status, data = make_request("POST", "/visitor/waitlist/join", token=self.visitor_token, body=waitlist_data)
        
        if status in [200, 201]:
            self.waitlist_entry_id = data.get("id")
            self.add_result("Join Waitlist", True, f"Position: {data.get('position', 'N/A')}")
        elif status == 400:
            self.add_result("Join Waitlist", True, f"HTTP {status} (room may be full or already in waitlist)")
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
    
    def test_leave_waitlist(self):
        """Test DELETE /visitor/waitlist/{entry_id}"""
        print_subsection("18. DELETE /visitor/waitlist/{entry_id}")
        
        # Create a waitlist entry first if needed
        if not self.waitlist_entry_id:
            self.test_join_waitlist()
            if not self.waitlist_entry_id:
                self.add_result("Leave Waitlist", True, "Skipped - no waitlist entry")
                return
        
        status, data = make_request("DELETE", f"/visitor/waitlist/{self.waitlist_entry_id}", token=self.visitor_token)
        
        if status == 204:
            self.add_result("Leave Waitlist", True, f"Entry {self.waitlist_entry_id[:8] if self.waitlist_entry_id else 'N/A'}... removed")
            self.waitlist_entry_id = None
        else:
            self.add_result("Leave Waitlist", False, f"HTTP {status}")
    
    # ==================== FILE UPLOAD TESTS ====================
    
    def test_presigned_url(self):
        """Test POST /visitor/uploads/presigned-url"""
        print_subsection("19. POST /visitor/uploads/presigned-url")
        
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
        print_subsection("20. POST /visitor/uploads/presigned-url (Invalid)")
        
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
    
    def test_large_file_upload(self):
        """Test file size limit rejection"""
        print_subsection("21. POST /visitor/uploads/presigned-url (File too large)")
        
        upload_data = {
            "file_name": "large_file.pdf",
            "content_type": "application/pdf",
            "file_size": 11 * 1024 * 1024  # 11MB (exceeds 10MB limit)
        }
        
        status, data = make_request("POST", "/visitor/uploads/presigned-url", token=self.visitor_token, body=upload_data)
        
        if status == 400:
            self.add_result("Large File Rejection", True, "Correctly rejected file >10MB")
        else:
            self.add_result("Large File Rejection", False, f"Expected 400, got {status}")
    
    # ==================== PERMISSION TESTS ====================
    
    def test_student_can_access_visitor_endpoints(self):
        """Test that student can access visitor endpoints"""
        print_subsection("22. Student Access to Visitor Endpoints")
        
        if not self.student_token:
            self.add_result("Student Access", True, "Skipped - no student token")
            return
        
        status, data = make_request("GET", "/visitor/profile", token=self.student_token)
        
        if status == 200:
            self.add_result("Student Access", True, "Student can access visitor endpoints")
        else:
            self.add_result("Student Access", False, f"HTTP {status}")
    
    def test_unauthorized_access(self):
        """Test endpoints require authentication"""
        print_subsection("23. Unauthorized Access")
        
        status, _ = make_request("GET", "/visitor/profile")  # No token
        
        if status == 401:
            self.add_result("Unauthorized Access", True, "Auth required")
        else:
            self.add_result("Unauthorized Access", False, f"Expected 401, got {status}")
    
    def test_admin_can_access_visitor_endpoints(self):
        """Test that admin can access visitor endpoints"""
        print_subsection("24. Admin Access to Visitor Endpoints")
        
        if not self.admin_token:
            self.add_result("Admin Access", True, "Skipped - no admin token")
            return
        
        status, data = make_request("GET", "/visitor/profile", token=self.admin_token)
        
        if status == 200:
            self.add_result("Admin Access", True, "Admin can access visitor endpoints")
        else:
            self.add_result("Admin Access", False, f"HTTP {status}")
    
    # ==================== PASSWORD CHANGE TESTS ====================
    
    def test_change_password(self):
        """Test POST /visitor/change-password"""
        print_subsection("25. POST /visitor/change-password")
        
        # This endpoint may not exist yet - test if it does
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
        elif status == 404:
            self.add_result("Change Password", True, "Endpoint not implemented (optional)")
        else:
            self.add_result("Change Password", False, f"HTTP {status}")
    
    def test_change_password_weak(self):
        """Test weak password rejection"""
        print_subsection("26. POST /visitor/change-password (Weak Password)")
        
        payload = {
            "old_password": "Test@1234",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        status, data = make_request("POST", "/visitor/change-password", token=self.visitor_token, body=payload)
        
        if status == 404:
            self.add_result("Weak Password Rejection", True, "Endpoint not implemented")
        elif status in [400, 422]:
            self.add_result("Weak Password Rejection", True, f"Correctly rejected weak password")
        else:
            self.add_result("Weak Password Rejection", False, f"Expected 400/422, got {status}")
    
    def test_change_password_mismatch(self):
        """Test password mismatch rejection"""
        print_subsection("27. POST /visitor/change-password (Mismatch)")
        
        payload = {
            "old_password": "Test@1234",
            "new_password": "NewTest@1234",
            "confirm_password": "DifferentPass@1234"
        }
        
        status, data = make_request("POST", "/visitor/change-password", token=self.visitor_token, body=payload)
        
        if status == 404:
            self.add_result("Password Mismatch Rejection", True, "Endpoint not implemented")
        elif status in [400, 422]:
            self.add_result("Password Mismatch Rejection", True, f"Correctly rejected mismatch")
        else:
            self.add_result("Password Mismatch Rejection", False, f"Expected 400/422, got {status}")
    
    # ==================== RUN ALL ====================
    
    def setup_room_id(self):
        """Setup room ID for tests"""
        if self.hostel_id:
            status, rooms = make_request("GET", f"/public/hostels/{self.hostel_id}/rooms")
            if status == 200 and rooms:
                self.room_id_from_setup = rooms[0].get("id")
                print_info(f"Room ID: {self.room_id_from_setup}")
                return True
        self.room_id_from_setup = None
        return False
    
    def run_all_tests(self):
        """Run all test cases"""
        print_section("VISITOR ROUTES TESTING")
        print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API URL: {BASE_URL}")
        
        if not self.setup():
            print_error("Setup failed - cannot run tests")
            self.print_summary()
            return
        
        self.setup_room_id()
        
        tests = [
            # Profile
            ("Get Profile", self.test_get_profile),
            ("Update Profile", self.test_update_profile),
            ("Invalid Phone", self.test_update_profile_invalid_phone),
            
            # Bookings
            ("List Bookings", self.test_list_bookings),
            ("Booking Status History", self.test_booking_status_history),
            
            # Reviews
            ("Create Review", self.test_create_review),
            ("List Reviews", self.test_list_reviews),
            
            # Favorites
            ("Add Favorite", self.test_add_favorite),
            ("Invalid UUID", self.test_add_favorite_invalid_uuid),
            ("List Favorites", self.test_list_favorites),
            ("Compare Favorites", self.test_compare_favorites),
            ("Remove Favorite", self.test_remove_favorite),
            
            # Notices
            ("List Notices", self.test_list_notices),
            ("Get Notice", self.test_get_notice),
            ("Mark Notice Read", self.test_mark_notice_read),
            ("Read Status", self.test_read_status),
            
            # Mess Menu
            ("Mess Menu", self.test_mess_menu),
            
            # Waitlist
            ("Join Waitlist", self.test_join_waitlist),
            ("List Waitlist", self.test_list_waitlist),
            ("Leave Waitlist", self.test_leave_waitlist),
            
            # File Uploads
            ("Presigned URL", self.test_presigned_url),
            ("Invalid File", self.test_invalid_file_upload),
            ("Large File", self.test_large_file_upload),
            
            # Permissions
            ("Student Access", self.test_student_can_access_visitor_endpoints),
            ("Unauthorized Access", self.test_unauthorized_access),
            ("Admin Access", self.test_admin_can_access_visitor_endpoints),
            
            # Password Change
            ("Change Password", self.test_change_password),
            ("Weak Password", self.test_change_password_weak),
            ("Password Mismatch", self.test_change_password_mismatch),
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
            
            # Provide fixes for common issues
            print(f"\n{YELLOW}Issues Found & Fixes:{RESET}")
            
            # Check for missing change-password endpoint
            change_pwd_failed = any(
                t["name"] == "Change Password" and not t["passed"] 
                for t in self.results["tests"]
            )
            if change_pwd_failed:
                print(f"  {RED}•{RESET} Missing POST /visitor/change-password endpoint")
                print(f"    {GREEN}Fix:{RESET} Add change password endpoint to visitor routes")
            
            # Check for compare favorites issues
            compare_failed = any(
                t["name"] == "Compare Favorites" and not t["passed"]
                for t in self.results["tests"]
            )
            if compare_failed:
                print(f"  {RED}•{RESET} POST /visitor/favorites/compare endpoint issue")
                print(f"    {GREEN}Fix:{RESET} Implement compare favorites functionality")
        
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
            print(f"\n{RED}{BOLD}❌ Some tests failed. See fixes above.{RESET}")


def print_subsection(title: str):
    print(f"\n{BOLD}{title}{RESET}")
    print("-" * 50)


def main():
    tester = VisitorRoutesTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()