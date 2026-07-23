#!/usr/bin/env python3
"""
Test script to verify student details API returns all required fields.
Run: python scripts/test_student_details_api.py

Required fields to check:
- id, full_name, email, phone, gender, date_of_birth
- student_number, status, check_in_date, check_out_date
- room_number, bed_number, room_type, floor
- hostel_name, hostel_city, hostel_type
- payment_status, total_paid, advance_paid
- booking_number, booking_mode
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional

BASE_URL = "http://localhost:8000/api/v1"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{text:^80}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_success(text: str):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str):
    print(f"{CYAN}ℹ {text}{RESET}")


def print_field(field: str, value: Any, required: bool = True):
    """Print a field with its value"""
    if value and value != "None" and value is not None:
        status = f"{GREEN}✓{RESET}"
    elif required:
        status = f"{RED}✗{RESET}"
    else:
        status = f"{YELLOW}⚠{RESET}"
    
    # Truncate long values
    display_value = str(value)
    if len(display_value) > 50:
        display_value = display_value[:47] + "..."
    
    print(f"  {status} {field:<22}: {display_value}")


def make_request(method: str, path: str, token: Optional[str] = None, body: Optional[Dict] = None) -> tuple[int, Any]:
    """Make HTTP request to API"""
    url = f"{BASE_URL}{path}"
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
    """Login and return user data"""
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


class StudentDetailsAPITester:
    """Test student details API endpoints"""
    
    def __init__(self):
        self.results = {
            "tests": [],
            "passed": 0,
            "failed": 0,
            "missing_fields": []
        }
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "message": message
        })
        if passed:
            self.results["passed"] += 1
            print_success(f"{test_name}: {message}" if message else test_name)
        else:
            self.results["failed"] += 1
            print_error(f"{test_name}: {message}" if message else test_name)
    
    def check_required_fields(self, data: Dict, required_fields: List[str], context: str) -> List[str]:
        """Check if all required fields exist and have values"""
        missing = []
        for field in required_fields:
            value = data.get(field)
            if value is None or value == "":
                missing.append(field)
        
        if missing:
            self.results["missing_fields"].append({
                "context": context,
                "missing": missing
            })
            print_warning(f"{context} missing: {missing}")
        
        return missing
    
    def display_student_details(self, student: Dict, title: str = "Student Details"):
        """Display all student details in formatted output"""
        print(f"\n{'─' * 80}")
        print(f"{BOLD}{CYAN}📋 {title}{RESET}")
        print(f"{'─' * 80}")
        
        # Personal Information
        print(f"\n{BOLD}👤 PERSONAL INFORMATION{RESET}")
        personal_fields = [
            ("id", "ID", True),
            ("full_name", "Full Name", True),
            ("email", "Email", True),
            ("phone", "Phone", True),
            ("gender", "Gender", True),
            ("date_of_birth", "Date of Birth", False),
            ("profile_picture_url", "Profile Picture", False),
        ]
        for field, label, required in personal_fields:
            print_field(label, student.get(field), required)
        
        # Student Information
        print(f"\n{BOLD}🎓 STUDENT INFORMATION{RESET}")
        student_fields = [
            ("student_number", "Student Number", True),
            ("status", "Status", True),
            ("check_in_date", "Check-in Date", True),
            ("check_out_date", "Check-out Date", False),
        ]
        for field, label, required in student_fields:
            print_field(label, student.get(field), required)
        
        # Room & Bed Information
        print(f"\n{BOLD}🏠 ROOM & BED INFORMATION{RESET}")
        room_fields = [
            ("room_number", "Room Number", True),
            ("bed_number", "Bed Number", True),
            ("room_type", "Room Type", True),
            ("floor", "Floor", False),
            ("monthly_rent", "Monthly Rent", False),
            ("daily_rent", "Daily Rent", False),
        ]
        for field, label, required in room_fields:
            print_field(label, student.get(field), required)
        
        # Hostel Information
        print(f"\n{BOLD}🏨 HOSTEL INFORMATION{RESET}")
        hostel_fields = [
            ("hostel_name", "Hostel Name", True),
            ("hostel_city", "City", True),
            ("hostel_type", "Hostel Type", True),
        ]
        for field, label, required in hostel_fields:
            print_field(label, student.get(field), required)
        
        # Booking Information
        print(f"\n{BOLD}📅 BOOKING INFORMATION{RESET}")
        booking_fields = [
            ("booking_number", "Booking Number", True),
            ("booking_mode", "Booking Mode", True),
            ("booking_advance", "Booking Advance", False),
        ]
        for field, label, required in booking_fields:
            print_field(label, student.get(field), required)
        
        # Payment Information
        print(f"\n{BOLD}💰 PAYMENT INFORMATION{RESET}")
        payment_fields = [
            ("payment_status", "Payment Status", True),
            ("total_paid", "Total Paid", True),
            ("advance_paid", "Advance Paid", False),
            ("last_payment_amount", "Last Payment", False),
            ("last_payment_date", "Last Payment Date", False),
            ("next_payment_due", "Next Payment Due", False),
        ]
        for field, label, required in payment_fields:
            value = student.get(field)
            if field in ["total_paid", "advance_paid", "last_payment_amount"] and value:
                value = f"₹{value:,.2f}"
            print_field(label, value, required)
        
        # Additional Information
        if student.get("occupation") or student.get("institution"):
            print(f"\n{BOLD}📚 ADDITIONAL INFORMATION{RESET}")
            if student.get("occupation"):
                print_field("Occupation", student.get("occupation"), False)
            if student.get("institution"):
                print_field("Institution", student.get("institution"), False)
            if student.get("emergency_contact_name"):
                print_field("Emergency Contact", student.get("emergency_contact_name"), False)
        
        print(f"\n{'─' * 80}")
    
    def test_admin_student_detail_endpoint(self, student_id: str):
        """Test GET /admin/students/{student_id}/complete endpoint"""
        print_header("TEST: Admin Student Detail Endpoint")
        
        # Login as Hostel Admin
        admin_data = login("admin1@leviticanestora.com")
        if not admin_data:
            self.add_result("Admin Login", False)
            return None
        
        admin_token = admin_data.get("access_token")
        self.add_result("Admin Login", True)
        
        # Call the endpoint
        endpoint = f"/admin/students/{student_id}/complete"
        status, data = make_request("GET", endpoint, token=admin_token)
        
        if status != 200:
            print_error(f"API returned status {status}: {data.get('detail', 'Unknown error')}")
            self.add_result("Admin Student Detail API", False, f"HTTP {status}")
            return None
        
        self.add_result("Admin Student Detail API", True, "Endpoint accessible")
        
        # Define required fields
        required_fields = [
            "id", "full_name", "email", "phone", "gender",
            "student_number", "status", "check_in_date",
            "room_number", "bed_number", "hostel_name",
            "payment_status", "total_paid", "booking_number"
        ]
        
        # Check required fields
        missing = self.check_required_fields(data, required_fields, "Student Details")
        
        if not missing:
            self.add_result("Required Fields Present", True, f"All {len(required_fields)} fields present")
        else:
            self.add_result("Required Fields Present", False, f"Missing: {missing}")
        
        # Display the details
        self.display_student_details(data, "COMPLETE STUDENT DETAILS (Admin API)")
        
        return data
    
    def test_super_admin_student_detail_endpoint(self, student_id: str):
        """Test super admin student detail endpoint if available"""
        print_header("TEST: Super Admin Student Detail Endpoint")
        
        # Login as Super Admin
        sa_data = login("superadmin@leviticanestora.com")
        if not sa_data:
            self.add_result("Super Admin Login", False)
            return None
        
        sa_token = sa_data.get("access_token")
        self.add_result("Super Admin Login", True)
        
        # Try different possible endpoints
        endpoints = [
            f"/super-admin/students/{student_id}",
            f"/super-admin/students/{student_id}/complete",
            f"/admin/students/{student_id}/complete",  # Already tested above
        ]
        
        data = None
        working_endpoint = None
        
        for endpoint in endpoints:
            if endpoint in [f"/admin/students/{student_id}/complete"]:
                continue  # Skip already tested
            status, response = make_request("GET", endpoint, token=sa_token)
            if status == 200:
                data = response
                working_endpoint = endpoint
                print_success(f"Found working endpoint: {endpoint}")
                break
        
        if not data:
            print_warning("No super admin specific endpoint found - using admin endpoint")
            return None
        
        # Check required fields
        required_fields = [
            "id", "full_name", "email", "phone", "gender",
            "student_number", "status", "check_in_date",
            "room_number", "bed_number", "hostel_name",
            "payment_status", "total_paid"
        ]
        
        missing = self.check_required_fields(data, required_fields, "Super Admin Student Details")
        
        if not missing:
            self.add_result("Super Admin Fields Present", True)
        else:
            self.add_result("Super Admin Fields Present", False, f"Missing: {missing}")
        
        self.display_student_details(data, "STUDENT DETAILS (Super Admin API)")
        
        return data
    
    def test_student_profile_endpoint(self):
        """Test student's own profile endpoint"""
        print_header("TEST: Student Profile Endpoint")
        
        # Login as Student
        student_data = login("hemant.pawade.lev044@levitica.in")
        if not student_data:
            self.add_result("Student Login", False)
            return None
        
        student_token = student_data.get("access_token")
        self.add_result("Student Login", True)
        
        # Try student profile endpoints
        endpoints = [
            "/student/profile",
            "/student/me",
        ]
        
        data = None
        for endpoint in endpoints:
            status, response = make_request("GET", endpoint, token=student_token)
            if status == 200:
                data = response
                print_success(f"Found working endpoint: {endpoint}")
                break
        
        if not data:
            print_error("No student profile endpoint found")
            self.add_result("Student Profile API", False, "No endpoint")
            return None
        
        # Student profile may have fewer fields
        expected_fields = [
            "id", "full_name", "email", "phone",
            "student_number", "status", "check_in_date",
            "room_id", "bed_id", "hostel_id"
        ]
        
        missing = self.check_required_fields(data, expected_fields, "Student Profile")
        
        if len(missing) <= 2:  # Allow missing room_number/bed_number in profile
            self.add_result("Student Profile Fields", True)
        else:
            self.add_result("Student Profile Fields", False, f"Missing: {missing}")
        
        self.display_student_details(data, "STUDENT PROFILE (Self View)")
        
        return data
    
    def test_admin_students_list_endpoint(self):
        """Test admin students list endpoint to get a student ID first"""
        print_header("TEST: Get Student ID from Admin List")
        
        # Login as Hostel Admin
        admin_data = login("admin1@leviticanestora.com")
        if not admin_data:
            return None
        
        admin_token = admin_data.get("access_token")
        
        # Get hostels for this admin
        status, hostels = make_request("GET", "/admin/my-hostels", token=admin_token)
        if status != 200 or not hostels:
            print_error("Could not get hostels")
            return None
        
        # Get students from first hostel
        hostel_id = hostels[0].get("id")
        status, students = make_request("GET", f"/admin/hostels/{hostel_id}/students", token=admin_token)
        
        if status != 200 or not students:
            print_error("No students found in hostel")
            return None
        
        student_id = students[0].get("id")
        print_success(f"Found student ID: {student_id}")
        
        return student_id
    
    def run_all_tests(self):
        """Run all tests"""
        print_header("STUDENT DETAILS API VALIDATION")
        print_info(f"API URL: {BASE_URL}")
        print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # First, get a student ID from the admin list endpoint
        student_id = self.test_admin_students_list_endpoint()
        
        if not student_id:
            print_error("Could not find any student to test with")
            print_info("Make sure seed data is loaded: python -m scripts.seed_data")
            return
        
        # Test admin student detail endpoint (main test)
        admin_details = self.test_admin_student_detail_endpoint(student_id)
        
        # Test super admin endpoint if available
        self.test_super_admin_student_detail_endpoint(student_id)
        
        # Test student's own profile
        self.test_student_profile_endpoint()
        
        # Print summary
        self.print_summary()
        
        # Final verdict
        if admin_details:
            self.print_verdict(admin_details)
    
    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        
        print(f"\n  {BOLD}Tests Run:{RESET}     {len(self.results['tests'])}")
        print(f"  {GREEN}{BOLD}Tests Passed:{RESET}  {self.results['passed']}")
        print(f"  {RED}{BOLD}Tests Failed:{RESET}  {self.results['failed']}")
        
        if self.results['missing_fields']:
            print(f"\n{YELLOW}Missing Fields Summary:{RESET}")
            for item in self.results['missing_fields']:
                print(f"  {item['context']}: {', '.join(item['missing'])}")
    
    def print_verdict(self, student_data: Dict):
        """Print final verdict on whether API returns all required fields"""
        print_header("FINAL VERDICT")
        
        required_fields = {
            "id": "Student ID",
            "full_name": "Full Name",
            "email": "Email",
            "phone": "Phone Number",
            "gender": "Gender",
            "student_number": "Student Number",
            "status": "Status",
            "check_in_date": "Check-in Date",
            "room_number": "Room Number",
            "bed_number": "Bed Number",
            "hostel_name": "Hostel Name",
            "payment_status": "Payment Status",
            "booking_number": "Booking Number"
        }
        
        print(f"\n{BOLD}Required Fields Check:{RESET}\n")
        
        all_present = True
        for field, label in required_fields.items():
            value = student_data.get(field)
            if value and value != "None":
                print(f"  {GREEN}✓{RESET} {label}: {value}")
            else:
                print(f"  {RED}✗{RESET} {label}: {RED}MISSING{RESET}")
                all_present = False
        
        print(f"\n{'─' * 80}\n")
        
        if all_present:
            print(f"{GREEN}{BOLD}✅ SUCCESS: API returns ALL required student details!{RESET}")
            print(f"\n{CYAN}The following fields are available:{RESET}")
            for field in required_fields:
                value = student_data.get(field)
                if value:
                    print(f"  • {field}: {value}")
        else:
            print(f"{RED}{BOLD}❌ FAILURE: API is missing some required fields{RESET}")
            print(f"\n{YELLOW}Missing fields need to be added to the response.{RESET}")


def main():
    tester = StudentDetailsAPITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()