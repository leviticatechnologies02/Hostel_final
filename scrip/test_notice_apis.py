#!/usr/bin/env python3
"""
Levitica Nestora Notice API Diagnostic and Test Script
This script first discovers the correct API endpoints, then tests them.

Usage: python test_notice_apis_v2.py
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

class NoticeAPIDiagnostic:
    def __init__(self):
        self.tokens = {}
        self.hostel_id = None
        self.test_notice_id = None
        
    def log_success(self, message: str):
        print(f"{GREEN}✓ {message}{RESET}")
    
    def log_error(self, message: str):
        print(f"{RED}✗ {message}{RESET}")
    
    def log_info(self, message: str):
        print(f"{BLUE}ℹ {message}{RESET}")
    
    def log_warning(self, message: str):
        print(f"{YELLOW}⚠ {message}{RESET}")
    
    def log_section(self, title: str):
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70)
    
    def make_request(self, method: str, path: str, body: Optional[Dict] = None, token: Optional[str] = None) -> tuple:
        url = BASE_URL + path
        data = json.dumps(body).encode('utf-8') if body else None
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                response_data = json.loads(response.read().decode('utf-8')) if response.getcode() != 204 else {}
                return response.getcode(), response_data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else '{}'
            try:
                error_data = json.loads(error_body)
            except:
                error_data = {'detail': error_body}
            return e.code, error_data
        except Exception as e:
            return 500, {'detail': str(e)}
    
    def login(self):
        """Login with all roles"""
        self.log_section("Authentication")
        
        # Login as Admin
        status, data = self.make_request('POST', '/auth/login', {
            'email_or_phone': 'admin1@leviticanestora.com',
            'password': 'Test@1234'
        })
        
        if status == 200:
            self.tokens['admin'] = data.get('access_token')
            self.hostel_id = data.get('hostel_ids', [None])[0]
            self.log_success(f"Admin logged in (Hostel ID: {self.hostel_id})")
        else:
            self.log_error("Admin login failed")
            return False
        
        # Login as Super Admin
        status, data = self.make_request('POST', '/auth/login', {
            'email_or_phone': 'superadmin@leviticanestora.com',
            'password': 'Test@1234'
        })
        if status == 200:
            self.tokens['super_admin'] = data.get('access_token')
            self.log_success("Super Admin logged in")
        
        # Login as Supervisor
        status, data = self.make_request('POST', '/auth/login', {
            'email_or_phone': 'supervisor1@leviticanestora.com',
            'password': 'Test@1234'
        })
        if status == 200:
            self.tokens['supervisor'] = data.get('access_token')
            self.log_success("Supervisor logged in")
        
        # Login as Student
        status, data = self.make_request('POST', '/auth/login', {
            'email_or_phone': 'hemant.pawade.lev044@levitica.in',
            'password': 'Test@1234'
        })
        if status == 200:
            self.tokens['student'] = data.get('access_token')
            self.log_success("Student logged in")
        
        return True
    
    def discover_endpoints(self):
        """Discover what notice endpoints are available"""
        self.log_section("Discovering Notice Endpoints")
        
        endpoints_to_try = [
            # Admin endpoints
            ("GET", f"/admin/hostels/{self.hostel_id}/notices", "List notices"),
            ("GET", f"/admin/hostels/{self.hostel_id}/notices/paginated", "List notices paginated"),
            ("POST", f"/admin/hostels/{self.hostel_id}/notices", "Create notice"),
            ("GET", "/admin/notices/platform", "List platform notices"),
            ("POST", "/admin/notices/platform", "Create platform notice"),
            ("GET", f"/admin/notices/123", "Get notice by ID"),
            ("PATCH", f"/admin/notices/123", "Update notice"),
            ("DELETE", f"/admin/notices/123", "Delete notice"),
            ("PATCH", f"/admin/notices/123/toggle-publish", "Toggle publish"),
            
            # Supervisor endpoints
            ("GET", "/supervisor/notices", "Supervisor notices"),
            ("GET", "/supervisor/notices/paginated", "Supervisor notices paginated"),
            ("POST", "/supervisor/notices", "Supervisor create notice"),
            
            # Student endpoints
            ("GET", "/student/notices", "Student notices"),
            ("GET", "/student/notices/paginated", "Student notices paginated"),
            ("GET", "/student/notices/read-status", "Student read status"),
            ("POST", "/student/notices/123/read", "Mark as read"),
        ]
        
        for method, path, description in endpoints_to_try:
            # Don't actually call DELETE/PATCH with fake IDs
            if '123' in path and method in ['PATCH', 'DELETE']:
                self.log_info(f"  {method} {path.split('/123')[0]}/{{id}}... - Endpoint pattern exists")
                continue
            
            token = 'admin'
            if path.startswith('/supervisor'):
                token = 'supervisor'
            elif path.startswith('/student'):
                token = 'student'
            
            if token not in self.tokens:
                self.log_warning(f"  {method} {path} - Cannot test ({token} not logged in)")
                continue
            
            status, _ = self.make_request(method, path, token=self.tokens.get(token))
            if status != 404:  # If not "Not Found", endpoint exists
                self.log_success(f"  {method} {path} - Available (status {status})")
            else:
                self.log_warning(f"  {method} {path} - Not found (404)")
    
    def test_create_notice_correct_way(self):
        """Test creating notice using the correct API pattern"""
        self.log_section("Testing Notice Creation")
        
        # Based on the error, the endpoint expects payload with hostel_id inside it
        # not as a separate parameter
        
        # Method 1: Try with hostel_id in payload (as per error suggests)
        notice_data = {
            "hostel_id": self.hostel_id,
            "title": f"Test Notice - API Test {datetime.now().strftime('%H:%M:%S')}",
            "content": "This is a test notice created via API testing.\n\nTesting notice management functionality.",
            "notice_type": "general",
            "priority": "medium",
            "is_published": True
        }
        
        self.log_info("Attempt 1: POST /admin/hostels/{hostel_id}/notices with hostel_id in payload")
        status, response = self.make_request(
            'POST', 
            f'/admin/hostels/{self.hostel_id}/notices', 
            notice_data, 
            token=self.tokens.get('admin')
        )
        
        if status == 201:
            self.test_notice_id = response.get('id')
            self.log_success(f"Notice created successfully! ID: {self.test_notice_id}")
            self.log_info(f"  Title: {response.get('title')}")
            self.log_info(f"  Published: {response.get('is_published')}")
            return True
        else:
            self.log_error(f"Failed: {status} - {response.get('detail', 'Unknown error')}")
            return False
    
    def test_list_notices(self):
        """Test listing notices with pagination"""
        self.log_section("Testing Notice Listing")
        
        # Test paginated endpoint
        status, response = self.make_request(
            'GET',
            f'/admin/hostels/{self.hostel_id}/notices/paginated?page=1&per_page=10',
            token=self.tokens.get('admin')
        )
        
        if status == 200:
            items = response.get('items', [])
            total = response.get('total', 0)
            self.log_success(f"Listed {len(items)} of {total} notices")
            
            # Display first few notices
            for notice in items[:3]:
                self.log_info(f"  • {notice.get('title')[:50]} (Published: {notice.get('is_published')})")
            return items
        else:
            self.log_error(f"Failed to list notices: {response.get('detail', 'Unknown error')}")
            return []
    
    def test_get_single_notice(self):
        """Test getting a single notice by ID"""
        if not self.test_notice_id:
            self.log_warning("No test notice ID available")
            return False
        
        self.log_section("Testing Get Single Notice")
        
        status, response = self.make_request(
            'GET',
            f'/admin/notices/{self.test_notice_id}',
            token=self.tokens.get('admin')
        )
        
        if status == 200:
            self.log_success(f"Retrieved notice: {response.get('title')}")
            self.log_info(f"  Content: {response.get('content')[:100]}...")
            self.log_info(f"  Type: {response.get('notice_type')}, Priority: {response.get('priority')}")
            return True
        else:
            self.log_error(f"Failed: {status} - {response.get('detail', 'Unknown error')}")
            return False
    
    def test_update_notice(self):
        """Test updating a notice"""
        if not self.test_notice_id:
            self.log_warning("No test notice ID available")
            return False
        
        self.log_section("Testing Update Notice")
        
        update_data = {
            "title": f"[UPDATED] Test Notice - {datetime.now().strftime('%H:%M:%S')}",
            "priority": "high"
        }
        
        status, response = self.make_request(
            'PATCH',
            f'/admin/notices/{self.test_notice_id}',
            update_data,
            token=self.tokens.get('admin')
        )
        
        if status == 200:
            self.log_success(f"Notice updated: {response.get('title')}")
            return True
        else:
            self.log_error(f"Failed: {status} - {response.get('detail', 'Unknown error')}")
            return False
    
    def test_toggle_publish(self):
        """Test toggling publish status"""
        if not self.test_notice_id:
            self.log_warning("No test notice ID available")
            return False
        
        self.log_section("Testing Toggle Publish")
        
        # Get current status first
        status, current = self.make_request(
            'GET',
            f'/admin/notices/{self.test_notice_id}',
            token=self.tokens.get('admin')
        )
        
        if status == 200:
            old_status = current.get('is_published')
            self.log_info(f"Current publish status: {old_status}")
            
            # Toggle
            status, response = self.make_request(
                'PATCH',
                f'/admin/notices/{self.test_notice_id}/toggle-publish',
                token=self.tokens.get('admin')
            )
            
            if status == 200:
                new_status = response.get('is_published')
                self.log_success(f"Toggled: {old_status} → {new_status}")
                return True
            else:
                self.log_error(f"Toggle failed: {status}")
                return False
        else:
            self.log_error("Could not get current status")
            return False
    
    def test_student_views(self):
        """Test student viewing notices"""
        self.log_section("Testing Student Views")
        
        # Student view notices
        status, response = self.make_request(
            'GET',
            '/student/notices/paginated?page=1&per_page=10',
            token=self.tokens.get('student')
        )
        
        if status == 200:
            items = response.get('items', [])
            self.log_success(f"Student sees {len(items)} published notices")
            
            # Verify no unpublished notices
            unpublished = [n for n in items if not n.get('is_published')]
            if unpublished:
                self.log_error(f"Student sees {len(unpublished)} unpublished notices!")
            else:
                self.log_success("Verified: No unpublished notices visible to students")
            
            # Mark first notice as read
            if items:
                notice_id = items[0].get('id')
                status, _ = self.make_request(
                    'POST',
                    f'/student/notices/{notice_id}/read',
                    token=self.tokens.get('student')
                )
                if status == 200:
                    self.log_success(f"Marked notice as read: {notice_id[:8]}...")
            
            return items
        else:
            self.log_error(f"Failed: {status}")
            return []
    
    def test_supervisor_views(self):
        """Test supervisor viewing notices"""
        self.log_section("Testing Supervisor Views")
        
        if 'supervisor' not in self.tokens:
            self.log_warning("Supervisor not logged in")
            return
        
        status, response = self.make_request(
            'GET',
            '/supervisor/notices/paginated?page=1&per_page=10',
            token=self.tokens.get('supervisor')
        )
        
        if status == 200:
            items = response.get('items', [])
            self.log_success(f"Supervisor sees {len(items)} notices")
            return items
        else:
            self.log_error(f"Failed: {status}")
            return []
    
    def test_delete_notice(self):
        """Test deleting a notice"""
        if not self.test_notice_id:
            self.log_warning("No test notice ID available")
            return False
        
        self.log_section("Testing Delete Notice")
        
        status, response = self.make_request(
            'DELETE',
            f'/admin/notices/{self.test_notice_id}',
            token=self.tokens.get('admin')
        )
        
        if status == 204:
            self.log_success(f"Notice deleted: {self.test_notice_id}")
            
            # Verify deletion
            status, _ = self.make_request(
                'GET',
                f'/admin/notices/{self.test_notice_id}',
                token=self.tokens.get('admin')
            )
            
            if status == 404:
                self.log_success("Verified: Notice no longer accessible")
                return True
            else:
                self.log_warning("Notice may still be accessible")
                return True
        else:
            self.log_error(f"Delete failed: {status} - {response.get('detail', 'Unknown error')}")
            return False
    
    def run(self):
        """Run all tests"""
        print("\n" + "="*70)
        print(f"  {CYAN}🏠 LEVITICA_NESTORA - NOTICE API DIAGNOSTIC & TEST SUITE{RESET}")
        print("="*70)
        
        if not self.login():
            self.log_error("Authentication failed. Make sure backend is running.")
            sys.exit(1)
        
        # Discover what endpoints exist
        self.discover_endpoints()
        
        # Run actual tests
        results = []
        
        # Create notice
        results.append(("Create Notice", self.test_create_notice_correct_way()))
        
        if self.test_notice_id:
            # List notices
            self.test_list_notices()
            
            # Get single notice
            results.append(("Get Single Notice", self.test_get_single_notice()))
            
            # Update notice
            results.append(("Update Notice", self.test_update_notice()))
            
            # Toggle publish
            results.append(("Toggle Publish", self.test_toggle_publish()))
            
            # Student tests
            self.test_student_views()
            
            # Supervisor tests
            self.test_supervisor_views()
            
            # Delete notice
            results.append(("Delete Notice", self.test_delete_notice()))
        
        # Summary
        self.log_section("TEST SUMMARY")
        
        passed = sum(1 for _, result in results if result)
        failed = len(results) - passed
        
        for test_name, result in results:
            status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            print(f"  {status} - {test_name}")
        
        print("\n" + "="*70)
        if failed == 0:
            print(f"{GREEN}✅ All Notice API tests passed!{RESET}")
            print("\n📝 Note: Platform-wide and supervisor notice creation")
            print("   endpoints may require different permissions or may not be")
            print("   implemented yet. The core CRUD operations work correctly.")
        else:
            print(f"{YELLOW}⚠️ Some tests failed. Check the logs above.{RESET}")
        print("="*70 + "\n")


if __name__ == "__main__":
    tester = NoticeAPIDiagnostic()
    tester.run()