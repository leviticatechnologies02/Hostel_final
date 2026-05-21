#!/usr/bin/env python3
"""
Test Subscription and Plan Routes - Comprehensive API Testing

Run: python scripts/test_subscription_routes.py
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


class SubscriptionRoutesTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.hostel_id = None
        self.subscription_id = None
        self.plan_id = None
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
        """Setup test data - login super admin and get hostel ID"""
        print_section("SETUP")
        
        # Login as Super Admin
        data = login("superadmin@stayease.com")
        if not data:
            print_error("Cannot proceed without super admin login")
            return False
        
        self.token = data.get("access_token")
        self.user_id = data.get("user_id")
        
        # Get a hostel ID
        status, hostels = make_request("GET", "/super-admin/hostels", token=self.token)
        if status == 200 and hostels:
            self.hostel_id = hostels[0].get("id")
            print_info(f"Using hostel: {hostels[0].get('name')} (ID: {self.hostel_id})")
        else:
            print_error("Could not fetch hostels")
            return False
        
        return True
    
    # ==================== PLAN TESTS ====================
    
    def test_list_plans(self):
        """Test GET /plans/plans"""
        print_section("1. GET /plans/plans - List Subscription Plans")
        
        status, data = make_request("GET", "/plans/plans", token=self.token)
        
        if status == 200:
            items = data.get("items", [])
            total = data.get("total", 0)
            self.add_result("List Plans", True, f"Found {total} plans")
            
            if items:
                print_info(f"  Sample: {items[0].get('name')} - ₹{items[0].get('price_monthly')}/month")
                if not self.plan_id:
                    self.plan_id = items[0].get("id")
        else:
            self.add_result("List Plans", False, f"HTTP {status}")
    
    def test_get_plan_details(self):
        """Test GET /plans/plans/{plan_id}"""
        print_section("2. GET /plans/plans/{plan_id} - Get Plan Details")
        
        if not self.plan_id:
            self.add_result("Get Plan Details", False, "No plan ID available")
            return
        
        status, data = make_request("GET", f"/plans/plans/{self.plan_id}", token=self.token)
        
        if status == 200:
            self.add_result("Get Plan Details", True, f"Plan: {data.get('name')} - {data.get('duration_type')}")
        else:
            self.add_result("Get Plan Details", False, f"HTTP {status}")
    
    def test_create_plan(self):
        """Test POST /plans/plans - Create a new plan"""
        print_section("3. POST /plans/plans - Create Subscription Plan")
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        plan_data = {
            "name": f"Test Plan {timestamp}",
            "code": f"TEST{timestamp[-6:]}",
            "description": "Test plan created by test script",
            "price_monthly": 999.0,
            "price_yearly": 9990.0,
            "duration_type": "monthly",
            "duration_days": 30,
            "hostel_limit": 5,
            "admin_limit": 3,
            "auto_renew_allowed": True,
            "status": "active",
            "features": [
                {"feature_name": "max_hostels", "feature_value": "5", "is_included": True},
                {"feature_name": "support", "feature_value": "24/7", "is_included": True}
            ]
        }
        
        status, data = make_request("POST", "/plans/plans", token=self.token, body=plan_data)
        
        if status == 201:
            self.plan_id = data.get("id")
            self.add_result("Create Plan", True, f"Created: {data.get('name')} (ID: {self.plan_id[:8] if self.plan_id else 'N/A'}...)")
        elif status == 409:
            self.add_result("Create Plan", True, "Plan already exists (skipped)")
        else:
            self.add_result("Create Plan", False, f"HTTP {status}")
    
    def test_update_plan(self):
        """Test PATCH /plans/plans/{plan_id} - Update a plan"""
        print_section("4. PATCH /plans/plans/{plan_id} - Update Plan")
        
        if not self.plan_id:
            self.add_result("Update Plan", False, "No plan ID available")
            return
        
        update_data = {
            "price_monthly": 1299.0,
            "description": "Updated description from test"
        }
        
        status, data = make_request("PATCH", f"/plans/plans/{self.plan_id}", token=self.token, body=update_data)
        
        if status == 200:
            self.add_result("Update Plan", True, f"Updated price: ₹{data.get('price_monthly')}")
        else:
            self.add_result("Update Plan", False, f"HTTP {status}")
    
    def test_toggle_plan_status(self):
        """Test PATCH /plans/plans/{plan_id}/toggle-status - Toggle plan status"""
        print_section("5. PATCH /plans/plans/{plan_id}/toggle-status - Toggle Plan Status")
        
        if not self.plan_id:
            self.add_result("Toggle Plan Status", False, "No plan ID available")
            return
        
        status, data = make_request("PATCH", f"/plans/plans/{self.plan_id}/toggle-status", token=self.token)
        
        if status == 200:
            new_status = data.get("status")
            self.add_result("Toggle Plan Status", True, f"New status: {new_status}")
            # Toggle back
            make_request("PATCH", f"/plans/plans/{self.plan_id}/toggle-status", token=self.token)
        else:
            self.add_result("Toggle Plan Status", False, f"HTTP {status}")
    
    def test_plan_auto_fill(self):
        """Test GET /plans/plans/{plan_id}/auto-fill - Plan auto-fill data"""
        print_section("6. GET /plans/plans/{plan_id}/auto-fill - Plan Auto-fill")
        
        if not self.plan_id:
            self.add_result("Plan Auto-fill", False, "No plan ID available")
            return
        
        start_date = (date.today() + timedelta(days=30)).isoformat()
        status, data = make_request("GET", f"/plans/plans/{self.plan_id}/auto-fill?start_date={start_date}", token=self.token)
        
        if status == 200:
            self.add_result("Plan Auto-fill", True, f"End date: {data.get('end_date')}, Hostel limit: {data.get('hostel_limit')}")
        else:
            self.add_result("Plan Auto-fill", False, f"HTTP {status}")
    
    def test_delete_plan(self):
        """Test DELETE /plans/plans/{plan_id} - Delete a plan"""
        print_section("7. DELETE /plans/plans/{plan_id} - Delete Plan")
        
        if not self.plan_id:
            self.add_result("Delete Plan", False, "No plan ID available")
            return
        
        # Create a temporary plan for deletion test
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        plan_data = {
            "name": f"Delete Test Plan {timestamp}",
            "code": f"DEL{timestamp[-6:]}",
            "description": "Plan to be deleted",
            "price_monthly": 499.0,
            "price_yearly": 4990.0,
            "duration_type": "monthly",
            "duration_days": 30,
            "hostel_limit": 1,
            "admin_limit": 1,
            "auto_renew_allowed": True,
            "status": "inactive",
            "features": []
        }
        
        status, data = make_request("POST", "/plans/plans", token=self.token, body=plan_data)
        
        if status != 201:
            self.add_result("Delete Plan", False, "Could not create test plan")
            return
        
        temp_plan_id = data.get("id")
        
        # Delete the temporary plan
        status, _ = make_request("DELETE", f"/plans/plans/{temp_plan_id}", token=self.token)
        
        if status == 204:
            self.add_result("Delete Plan", True, "Plan deleted successfully")
        else:
            self.add_result("Delete Plan", False, f"HTTP {status}")
    
    # ==================== SUBSCRIPTION TESTS ====================
    
    def test_list_subscriptions(self):
        """Test GET /super-admin/subscriptions"""
        print_section("8. GET /super-admin/subscriptions - List All Subscriptions")
        
        status, data = make_request("GET", "/super-admin/subscriptions", token=self.token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Subscriptions", True, f"Found {count} subscriptions")
            
            if count > 0 and isinstance(data, list) and not self.subscription_id:
                self.subscription_id = data[0].get("id")
                print_info(f"  Sample: {data[0].get('hostel_name')} - {data[0].get('tier')} (₹{data[0].get('price_monthly')})")
        else:
            self.add_result("List Subscriptions", False, f"HTTP {status}")
    
    def test_list_subscriptions_by_status(self):
        """Test GET /super-admin/subscriptions?status_filter=active"""
        print_section("9. GET /super-admin/subscriptions?status_filter=active - Filter by Status")
        
        status, data = make_request("GET", "/super-admin/subscriptions?status_filter=active", token=self.token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Subscriptions (Active)", True, f"Found {count} active subscriptions")
        else:
            self.add_result("List Subscriptions (Active)", False, f"HTTP {status}")
    
    def test_list_subscriptions_by_hostel(self):
        """Test GET /super-admin/subscriptions?hostel_id={id}"""
        print_section("10. GET /super-admin/subscriptions?hostel_id={id} - Filter by Hostel")
        
        status, data = make_request("GET", f"/super-admin/subscriptions?hostel_id={self.hostel_id}", token=self.token)
        
        if status == 200:
            count = len(data) if isinstance(data, list) else 0
            self.add_result("List Subscriptions by Hostel", True, f"Found {count} subscriptions for this hostel")
        else:
            self.add_result("List Subscriptions by Hostel", False, f"HTTP {status}")
    
    def test_get_subscription_by_id(self):
        """Test GET /super-admin/subscriptions/{id}"""
        print_section("11. GET /super-admin/subscriptions/{id} - Get Subscription by ID")
        
        if not self.subscription_id:
            self.add_result("Get Subscription by ID", False, "No subscription ID available")
            return
        
        status, data = make_request("GET", f"/super-admin/subscriptions/{self.subscription_id}", token=self.token)
        
        if status == 200:
            self.add_result("Get Subscription by ID", True, f"Tier: {data.get('tier')}, Status: {data.get('status')}")
        else:
            self.add_result("Get Subscription by ID", False, f"HTTP {status}")
    
    def test_get_nonexistent_subscription(self):
        """Test GET /super-admin/subscriptions/invalid-id - 404 error"""
        print_section("12. GET /super-admin/subscriptions/invalid-id - 404 Error")
        
        fake_id = "00000000-0000-0000-0000-000000000000"
        status, data = make_request("GET", f"/super-admin/subscriptions/{fake_id}", token=self.token)
        
        if status == 404:
            self.add_result("Get Nonexistent Subscription (404)", True, "Correctly returned 404")
        else:
            self.add_result("Get Nonexistent Subscription (404)", False, f"Expected 404, got {status}")
    
    def test_create_subscription(self):
        """Test POST /super-admin/subscriptions"""
        print_section("13. POST /super-admin/subscriptions - Create Subscription")
        
        # First check if hostel already has active subscription
        status, existing = make_request("GET", f"/super-admin/subscriptions?hostel_id={self.hostel_id}", token=self.token)
        
        if status == 200 and existing:
            for sub in existing:
                if sub.get("status") == "active":
                    # Cancel existing active subscription
                    make_request("POST", f"/super-admin/subscriptions/{sub.get('id')}/cancel", token=self.token)
                    print_info(f"Cancelled existing active subscription: {sub.get('id')[:8]}...")
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        subscription_data = {
            "hostel_id": self.hostel_id,
            "tier": f"test_tier_{timestamp[-6:]}",
            "price_monthly": 2999.0,
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=365)).isoformat(),
            "auto_renew": False,
            "status": "active"
        }
        
        status, data = make_request("POST", "/super-admin/subscriptions", token=self.token, body=subscription_data)
        
        if status == 201:
            self.subscription_id = data.get("id")
            self.add_result("Create Subscription", True, f"Created: {data.get('tier')} (ID: {self.subscription_id[:8] if self.subscription_id else 'N/A'}...)")
        elif status == 409:
            self.add_result("Create Subscription", True, "Hostel already has active subscription (conflict)")
        else:
            self.add_result("Create Subscription", False, f"HTTP {status}")
    
    def test_update_subscription(self):
        """Test PATCH /super-admin/subscriptions/{id}"""
        print_section("14. PATCH /super-admin/subscriptions/{id} - Update Subscription")
        
        if not self.subscription_id:
            # Try to get an existing subscription
            status, subs = make_request("GET", "/super-admin/subscriptions", token=self.token)
            if status == 200 and subs:
                self.subscription_id = subs[0].get("id")
        
        if not self.subscription_id:
            self.add_result("Update Subscription", False, "No subscription ID available")
            return
        
        update_data = {
            "tier": "updated_tier",
            "price_monthly": 3999.0,
            "auto_renew": True
        }
        
        status, data = make_request("PATCH", f"/super-admin/subscriptions/{self.subscription_id}", token=self.token, body=update_data)
        
        if status == 200:
            self.add_result("Update Subscription", True, f"Updated to tier: {data.get('tier')}, price: ₹{data.get('price_monthly')}")
        else:
            self.add_result("Update Subscription", False, f"HTTP {status}")
    
    def test_cancel_subscription(self):
        """Test POST /super-admin/subscriptions/{id}/cancel"""
        print_section("15. POST /super-admin/subscriptions/{id}/cancel - Cancel Subscription")
        
        if not self.subscription_id:
            self.add_result("Cancel Subscription", False, "No subscription ID available")
            return
        
        status, data = make_request("POST", f"/super-admin/subscriptions/{self.subscription_id}/cancel", token=self.token)
        
        if status == 200:
            self.add_result("Cancel Subscription", True, f"Status: {data.get('status')}, Auto-renew: {data.get('auto_renew')}")
        else:
            self.add_result("Cancel Subscription", False, f"HTTP {status}")
    
    def test_subscription_stats(self):
        """Test GET /super-admin/subscriptions/stats"""
        print_section("16. GET /super-admin/subscriptions/stats - Subscription Statistics")
        
        status, data = make_request("GET", "/super-admin/subscriptions/stats", token=self.token)
        
        if status == 200:
            total = data.get("total_subscriptions", 0)
            active = data.get("active_subscriptions", 0)
            revenue = data.get("monthly_recurring_revenue", 0)
            self.add_result("Subscription Stats", True, f"Total: {total}, Active: {active}, Revenue: ₹{revenue:,.0f}")
        else:
            self.add_result("Subscription Stats", False, f"HTTP {status}")
    
    def test_hostel_subscription_status(self):
        """Test GET /public/hostels/{hostel_id}/subscription-status"""
        print_section("17. GET /public/hostels/{hostel_id}/subscription-status")
        
        status, data = make_request("GET", f"/public/hostels/{self.hostel_id}/subscription-status")
        
        if status == 200:
            can_book = data.get("can_book", False)
            has_sub = data.get("has_subscription", False)
            self.add_result("Hostel Subscription Status", True, f"Can book: {can_book}, Has subscription: {has_sub}")
        else:
            self.add_result("Hostel Subscription Status", False, f"HTTP {status}")
    
    def test_subscription_from_plan(self):
        """Test POST /plans/subscriptions/from-plan - Create subscription from plan"""
        print_section("18. POST /plans/subscriptions/from-plan - Create Subscription from Plan")
        
        if not self.plan_id:
            self.add_result("Subscription from Plan", False, "No plan ID available")
            return
        
        # Cancel existing active subscription for this hostel
        status, existing = make_request("GET", f"/super-admin/subscriptions?hostel_id={self.hostel_id}", token=self.token)
        if status == 200 and existing:
            for sub in existing:
                if sub.get("status") == "active":
                    make_request("POST", f"/super-admin/subscriptions/{sub.get('id')}/cancel", token=self.token)
                    print_info(f"Cancelled existing active subscription for test")
        
        subscription_data = {
            "hostel_id": self.hostel_id,
            "plan_id": self.plan_id,
            "start_date": (date.today() + timedelta(days=1)).isoformat(),
            "auto_renew": True
        }
        
        status, data = make_request("POST", "/plans/subscriptions/from-plan", token=self.token, body=subscription_data)
        
        if status == 200 or status == 201:
            self.add_result("Subscription from Plan", True, f"Created subscription from plan")
        else:
            self.add_result("Subscription from Plan", False, f"HTTP {status}")
    
    # ==================== RUN ALL ====================
    
    def run_all_tests(self):
        """Run all test cases"""
        print_section("SUBSCRIPTION ROUTES TESTING")
        print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API URL: {BASE_URL}")
        
        if not self.setup():
            print_error("Setup failed - cannot run tests")
            self.print_summary()
            return
        
        tests = [
            # Plan tests
            ("List Plans", self.test_list_plans),
            ("Get Plan Details", self.test_get_plan_details),
            ("Create Plan", self.test_create_plan),
            ("Update Plan", self.test_update_plan),
            ("Toggle Plan Status", self.test_toggle_plan_status),
            ("Plan Auto-fill", self.test_plan_auto_fill),
            ("Delete Plan", self.test_delete_plan),
            
            # Subscription tests
            ("List Subscriptions", self.test_list_subscriptions),
            ("List Subscriptions by Status", self.test_list_subscriptions_by_status),
            ("List Subscriptions by Hostel", self.test_list_subscriptions_by_hostel),
            ("Get Subscription by ID", self.test_get_subscription_by_id),
            ("Get Nonexistent Subscription", self.test_get_nonexistent_subscription),
            ("Create Subscription", self.test_create_subscription),
            ("Update Subscription", self.test_update_subscription),
            ("Cancel Subscription", self.test_cancel_subscription),
            ("Subscription Stats", self.test_subscription_stats),
            ("Hostel Subscription Status", self.test_hostel_subscription_status),
            ("Subscription from Plan", self.test_subscription_from_plan),
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
        
        # List all available endpoints
        print(f"\n{CYAN}{BOLD}Available Subscription/Plan Endpoints:{RESET}")
        endpoints = [
            "GET    /plans/plans",
            "POST   /plans/plans",
            "GET    /plans/plans/{id}",
            "PATCH  /plans/plans/{id}",
            "DELETE /plans/plans/{id}",
            "PATCH  /plans/plans/{id}/toggle-status",
            "GET    /plans/plans/{id}/auto-fill",
            "POST   /plans/subscriptions/from-plan",
            "GET    /super-admin/subscriptions",
            "GET    /super-admin/subscriptions?status_filter=active",
            "GET    /super-admin/subscriptions?hostel_id={id}",
            "GET    /super-admin/subscriptions/{id}",
            "POST   /super-admin/subscriptions",
            "PATCH  /super-admin/subscriptions/{id}",
            "POST   /super-admin/subscriptions/{id}/cancel",
            "DELETE /super-admin/subscriptions/{id}",
            "GET    /super-admin/subscriptions/stats",
            "GET    /public/hostels/{id}/subscription-status",
            "GET    /super-admin/hostels/{hostel_id}/subscription-limit-status",
        ]
        for ep in endpoints:
            print(f"  {ep}")
        
        if self.results["failed"] == 0:
            print(f"\n{GREEN}{BOLD}✅ ALL TESTS PASSED! Subscription routes are working correctly.{RESET}")
        else:
            print(f"\n{RED}{BOLD}❌ Some tests failed. Check the errors above.{RESET}")
            print(f"\n{YELLOW}Common issues:{RESET}")
            print("  1. Make sure backend is running: uvicorn app.main:app --reload")
            print("  2. Check database connection")
            print("  3. Verify seed data has some subscriptions")


if __name__ == "__main__":
    tester = SubscriptionRoutesTester()
    tester.run_all_tests()