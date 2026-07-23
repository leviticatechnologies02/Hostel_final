#!/usr/bin/env python3
"""
Student Details API Test & Validation Script
Tests if backend returns complete student details including:
- name, id, email, phone
- bed number, room number, status
- payment status, check-in/out dates, gender
- student number, hostel info

Run: python test_student_details.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any, List

BASE_URL = "http://localhost:8000/api/v1"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_header(text: str):
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text:^80}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(text: str):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str):
    print(f"{CYAN}ℹ {text}{RESET}")


def print_field_status(field: str, exists: bool, value: any = None):
    """Print field validation status"""
    if exists:
        display_value = str(value)[:50] if value else "None"
        print(f"  {GREEN}✓{RESET} {field:<20} : {display_value}")
    else:
        print(f"  {RED}✗{RESET} {field:<20} : {RED}MISSING{RESET}")


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


class StudentDetailsTester:
    """Test student details from various endpoints"""
    
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
        """Check if all required fields exist in data"""
        missing = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing.append(field)
        
        if missing:
            self.results["missing_fields"].append({
                "context": context,
                "missing": missing
            })
            print_warning(f"{context} missing fields: {missing}")
        
        return missing
    
    def display_student_details(self, student: Dict, title: str = "Student Details"):
        """Display student details in formatted output"""
        print(f"\n{'─' * 80}")
        print(f"{BLUE}📋 {title}{RESET}")
        print(f"{'─' * 80}")
        
        # Define field groups
        basic_fields = [
            ('id', 'ID'),
            ('student_number', 'Student Number'),
            ('full_name', 'Full Name'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('gender', 'Gender'),
        ]
        
        room_bed_fields = [
            ('room_number', 'Room Number'),
            ('bed_number', 'Bed Number'),
            ('room_type', 'Room Type'),
            ('floor', 'Floor'),
        ]
        
        date_fields = [
            ('check_in_date', 'Check-in Date'),
            ('check_out_date', 'Check-out Date'),
        ]
        
        status_fields = [
            ('status', 'Status'),
            ('payment_status', 'Payment Status'),
            ('booking_status', 'Booking Status'),
        ]
        
        hostel_fields = [
            ('hostel_name', 'Hostel Name'),
            ('hostel_city', 'City'),
            ('hostel_type', 'Hostel Type'),
        ]
        
        # Print Basic Info
        print(f"\n{CYAN}👤 PERSONAL INFORMATION{RESET}")
        for field, label in basic_fields:
            value = student.get(field, 'N/A')
            if value and value != 'N/A':
                print(f"  {label:<18}: {value}")
            else:
                print(f"  {label:<18}: {YELLOW}{value}{RESET}")
        
        # Print Room & Bed
        print(f"\n{CYAN}🏠 ROOM & BED INFORMATION{RESET}")
        for field, label in room_bed_fields:
            value = student.get(field, 'N/A')
            if value and value != 'N/A':
                print(f"  {label:<18}: {value}")
            else:
                print(f"  {label:<18}: {YELLOW}{value}{RESET}")
        
        # Print Dates
        print(f"\n{CYAN}📅 STAY DATES{RESET}")
        for field, label in date_fields:
            value = student.get(field, 'N/A')
            if value and value != 'N/A':
                print(f"  {label:<18}: {value}")
            else:
                print(f"  {label:<18}: {YELLOW}{value}{RESET}")
        
        # Print Status
        print(f"\n{CYAN}📊 STATUS{RESET}")
        for field, label in status_fields:
            value = student.get(field, 'N/A')
            if value and value != 'N/A':
                color = GREEN if value in ['active', 'paid', 'approved'] else YELLOW
                print(f"  {label:<18}: {color}{value}{RESET}")
            else:
                print(f"  {label:<18}: {YELLOW}{value}{RESET}")
        
        # Print Hostel Info
        if any(student.get(f, '') for f, _ in hostel_fields):
            print(f"\n{CYAN}🏨 HOSTEL INFORMATION{RESET}")
            for field, label in hostel_fields:
                value = student.get(field, 'N/A')
                if value and value != 'N/A':
                    print(f"  {label:<18}: {value}")
        
        # Print Payment Info
        if student.get('total_paid') is not None:
            print(f"\n{CYAN}💰 PAYMENT DETAILS{RESET}")
            print(f"  Total Paid        : ₹{student.get('total_paid', 0):,.0f}")
            print(f"  Advance Paid      : ₹{student.get('advance_paid', 0):,.0f}")
            if student.get('last_payment_date'):
                print(f"  Last Payment      : {student.get('last_payment_date')}")
        
        print(f"{'─' * 80}")
    
    def test_super_admin_students_endpoint(self):
        """Test GET /super-admin/students endpoint"""
        print_header("TEST 1: Super Admin Students List Endpoint")
        
        # Login as Super Admin
        sa_data = login("superadmin@leviticanestora.com")
        if not sa_data:
            self.add_result("Super Admin Login", False, "Could not login")
            return None
        
        sa_token = sa_data.get("access_token")
        self.add_result("Super Admin Login", True)
        
        # Try different possible endpoints
        endpoints = [
            ("/super-admin/students", "New endpoint"),
            ("/super-admin/students/all", "Alternative endpoint"),
            ("/admin/students/all", "Admin alternative"),
        ]
        
        students = None
        working_endpoint = None
        
        for endpoint, desc in endpoints:
            status, data = make_request("GET", endpoint, token=sa_token)
            if status == 200:
                if isinstance(data, list):
                    students = data
                    working_endpoint = endpoint
                    print_success(f"Found working endpoint: {endpoint}")
                    break
                elif isinstance(data, dict) and 'items' in data:
                    students = data['items']
                    working_endpoint = endpoint
                    print_success(f"Found working endpoint (paginated): {endpoint}")
                    break
        
        if students is None:
            # Fallback: Get students from hostels
            print_info("Trying to fetch students via hostels...")
            status, hostels = make_request("GET", "/super-admin/hostels", token=sa_token)
            
            if status == 200 and isinstance(hostels, list):
                students = []
                for hostel in hostels[:2]:  # Limit to first 2 hostels
                    hostel_id = hostel.get('id')
                    if hostel_id:
                        # Try to get students from this hostel
                        s_status, s_data = make_request("GET", f"/admin/hostels/{hostel_id}/students", token=sa_token)
                        if s_status == 200 and isinstance(s_data, list):
                            for s in s_data:
                                s['hostel_name'] = hostel.get('name', 'Unknown')
                            students.extend(s_data)
        
        if not students:
            self.add_result("Fetch Students List", False, "No students found or endpoint not available")
            return None
        
        self.add_result("Fetch Students List", True, f"Found {len(students)} students")
        
        # Check required fields in first few students
        required_fields = ['id', 'full_name', 'email', 'student_number', 'status']
        
        for i, student in enumerate(students[:3]):
            missing = self.check_required_fields(student, required_fields, f"Student {i+1}")
            if not missing:
                self.add_result(f"Student {i+1} Required Fields", True)
            else:
                self.add_result(f"Student {i+1} Required Fields", False, f"Missing: {missing}")
        
        return students
    
    def test_student_detail_endpoint(self, student_id: str):
        """Test getting complete student details"""
        print_header(f"TEST 2: Complete Student Details for ID: {student_id}")
        
        # Required fields for complete student view
        required_fields = [
            'id', 'full_name', 'email', 'phone', 'gender',
            'student_number', 'room_number', 'bed_number',
            'check_in_date', 'check_out_date', 'status',
            'payment_status', 'hostel_name'
        ]
        
        # Login as Super Admin
        sa_data = login("superadmin@leviticanestora.com")
        if not sa_data:
            return None
        
        sa_token = sa_data.get("access_token")
        
        # Try different detail endpoints
        endpoints = [
            (f"/super-admin/students/{student_id}", "Super Admin endpoint"),
            (f"/admin/students/{student_id}/complete", "Admin complete endpoint"),
            (f"/admin/students/{student_id}", "Admin endpoint"),
            (f"/student/profile", "Student profile endpoint (needs student token)"),
        ]
        
        student_detail = None
        
        for endpoint, desc in endpoints:
            status, data = make_request("GET", endpoint, token=sa_token)
            if status == 200:
                if isinstance(data, dict) and len(data) > 0:
                    student_detail = data
                    print_success(f"Found working detail endpoint: {endpoint}")
                    break
        
        if not student_detail:
            # Try with student token
            print_info("Trying with student token...")
            student_login = login("hemant.pawade.lev044@levitica.in")
            if student_login:
                s_token = student_login.get("access_token")
                status, data = make_request("GET", "/student/profile", token=s_token)
                if status == 200:
                    student_detail = data
                    print_success("Found student profile endpoint")
        
        if not student_detail:
            self.add_result("Get Student Details", False, "No detail endpoint available")
            return None
        
        # Check all required fields
        missing = self.check_required_fields(student_detail, required_fields, "Student Details")
        
        if not missing:
            self.add_result("Student Details Complete", True, "All required fields present")
        else:
            self.add_result("Student Details Complete", False, f"Missing {len(missing)} fields")
        
        # Display the student details
        self.display_student_details(student_detail, "COMPLETE STUDENT DETAILS")
        
        return student_detail
    
    def test_admin_student_list(self):
        """Test admin endpoints for student lists"""
        print_header("TEST 3: Admin Student List Endpoints")
        
        # Login as Hostel Admin
        admin_data = login("admin1@leviticanestora.com")
        if not admin_data:
            self.add_result("Admin Login", False)
            return None
        
        admin_token = admin_data.get("access_token")
        self.add_result("Admin Login", True)
        
        # Get hostels for this admin
        status, hostels = make_request("GET", "/admin/my-hostels", token=admin_token)
        
        if status != 200 or not hostels:
            self.add_result("Get Admin Hostels", False, "No hostels found")
            return None
        
        self.add_result("Get Admin Hostels", True, f"Found {len(hostels)} hostels")
        
        all_students = []
        
        for hostel in hostels:
            hostel_id = hostel.get('id')
            hostel_name = hostel.get('name')
            
            status, students = make_request("GET", f"/admin/hostels/{hostel_id}/students", token=admin_token)
            
            if status == 200 and isinstance(students, list):
                print_success(f"Hostel '{hostel_name}': {len(students)} students")
                
                # Enhance student data with hostel name
                for s in students:
                    s['hostel_name'] = hostel_name
                
                all_students.extend(students)
                
                # Check first student's fields
                if students:
                    required_fields = ['id', 'full_name', 'email', 'student_number']
                    missing = self.check_required_fields(students[0], required_fields, f"Student in {hostel_name}")
                    
                    # Check for room and bed info
                    if 'room_number' not in students[0] or students[0].get('room_number') is None:
                        print_warning(f"  Room number missing for student in {hostel_name}")
                    if 'bed_number' not in students[0] or students[0].get('bed_number') is None:
                        print_warning(f"  Bed number missing for student in {hostel_name}")
                    if 'payment_status' not in students[0]:
                        print_warning(f"  Payment status missing for student in {hostel_name}")
            else:
                print_error(f"Failed to get students for hostel {hostel_name}: {status}")
        
        self.add_result("Fetch Students Across Hostels", True, f"Total {len(all_students)} students")
        
        return all_students
    
    def test_payment_status_endpoint(self, student_id: str):
        """Test getting payment status for a student"""
        print_header("TEST 4: Student Payment Status")
        
        sa_data = login("superadmin@leviticanestora.com")
        if not sa_data:
            return
        
        sa_token = sa_data.get("access_token")
        
        # Try payment endpoints
        endpoints = [
            (f"/super-admin/students/{student_id}/payments", "Super Admin"),
            (f"/admin/students/{student_id}/payments", "Admin"),
            (f"/student/payments", "Student (needs student token)"),
        ]
        
        payments = None
        
        for endpoint, desc in endpoints:
            status, data = make_request("GET", endpoint, token=sa_token)
            if status == 200:
                if isinstance(data, list):
                    payments = data
                    print_success(f"Found payment endpoint: {endpoint} ({len(payments)} records)")
                    break
                elif isinstance(data, dict):
                    payments = data
                    print_success(f"Found payment endpoint: {endpoint}")
                    break
        
        if payments:
            self.add_result("Payment Status Available", True)
            if isinstance(payments, list):
                total = sum(p.get('amount', 0) for p in payments if p.get('status') == 'captured')
                print_info(f"Total payments: ₹{total:,.0f}")
        else:
            self.add_result("Payment Status Available", False, "No payment endpoint found")
        
        return payments
    
    def run_all_tests(self):
        """Run all tests"""
        print_header("STUDENT DETAILS API VALIDATION")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API URL: {BASE_URL}")
        
        # Test 1: Get students list
        students = self.test_super_admin_students_endpoint()
        
        # Test 2: Get complete details for first student
        student_detail = None
        if students and len(students) > 0:
            student_id = students[0].get('id')
            if student_id:
                student_detail = self.test_student_detail_endpoint(student_id)
        
        # Test 3: Admin student list
        admin_students = self.test_admin_student_list()
        
        # Test 4: Payment status
        if student_detail and student_detail.get('id'):
            self.test_payment_status_endpoint(student_detail.get('id'))
        elif students and len(students) > 0:
            self.test_payment_status_endpoint(students[0].get('id'))
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        
        print(f"\n  {BLUE}Tests Run:{RESET}     {len(self.results['tests'])}")
        print(f"  {GREEN}Tests Passed:{RESET}  {self.results['passed']}")
        print(f"  {RED}Tests Failed:{RESET}  {self.results['failed']}")
        
        if self.results['missing_fields']:
            print(f"\n{YELLOW}Missing Fields Summary:{RESET}")
            for item in self.results['missing_fields']:
                print(f"  {item['context']}: {item['missing']}")
        
        # Calculate completion percentage
        required_fields_count = 12  # name, id, email, phone, bed_number, room_number, status, payment_status, check_in, check_out, gender, student_number
        found_fields = set()
        
        for item in self.results['missing_fields']:
            for field in item['missing']:
                # Track missing fields
                pass
        
        if self.results['failed'] == 0:
            print(f"\n{GREEN}✅ All tests passed! Student details API is working correctly.{RESET}")
        else:
            print(f"\n{RED}❌ Some tests failed. See issues above.{RESET}")
            print(f"\n{YELLOW}Recommendations:{RESET}")
            print("  1. Add GET /super-admin/students endpoint for super admin")
            print("  2. Add GET /admin/students/{id}/complete endpoint with all fields")
            print("  3. Include room_number, bed_number, and payment_status in student responses")
            print("  4. Add gender field from booking table to student details")


# Alternative: Direct database check script
def create_direct_db_check_script():
    """Create a separate script to check database directly"""
    script_content = '''#!/usr/bin/env python3
"""
Direct Database Check for Student Details
Run this if API endpoints are not available

Install: pip install asyncpg
Run: python check_db_students.py
"""

import asyncio
import asyncpg
from datetime import datetime

async def check_students():
    conn = await asyncpg.connect(
        "postgresql://postgres:Kiran$1234@localhost:5432/leviticanestora_dev"
    )
    
    print("\\n" + "="*80)
    print("  DATABASE STUDENT DETAILS CHECK")
    print("="*80)
    
    # Query students with all related info
    rows = await conn.fetch("""
        SELECT 
            s.id as student_id,
            s.student_number,
            s.check_in_date,
            s.check_out_date,
            s.status as student_status,
            u.id as user_id,
            u.full_name,
            u.email,
            u.phone,
            b.gender,
            b.date_of_birth,
            r.room_number,
            r.room_type,
            r.floor,
            bed.bed_number,
            bk.booking_number,
            bk.booking_mode,
            bk.payment_status as booking_payment_status,
            h.name as hostel_name,
            h.city as hostel_city,
            h.hostel_type
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN bookings bk ON bk.id = s.booking_id
        LEFT JOIN rooms r ON r.id = s.room_id
        LEFT JOIN beds bed ON bed.id = s.bed_id
        LEFT JOIN hostels h ON h.id = s.hostel_id
        LEFT JOIN booking b ON b.id = s.booking_id
        LIMIT 5
    """)
    
    print(f"\\n{CYAN}Found {len(rows)} students in database{RESET}\\n")
    
    required_fields = ['full_name', 'email', 'phone', 'room_number', 'bed_number', 
                      'gender', 'check_in_date', 'student_status']
    
    for i, row in enumerate(rows, 1):
        print(f"{'─'*70}")
        print(f"{BLUE}Student #{i}{RESET}")
        print(f"{'─'*70}")
        
        for field in required_fields:
            value = row[field]
            if value:
                print(f"  {field:<20}: {value}")
            else:
                print(f"  {field:<20}: {YELLOW}NULL{RESET}")
        
        print()
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_students())
'''
    
    with open("check_db_students.py", "w") as f:
        f.write(script_content)
    print_info("Created database check script: check_db_students.py")


if __name__ == "__main__":
    tester = StudentDetailsTester()
    tester.run_all_tests()
    
    # Create database check script as fallback
    create_direct_db_check_script()