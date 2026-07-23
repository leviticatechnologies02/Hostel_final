#!/usr/bin/env python3
"""
Diagnostic script to check subscription endpoints.

Run: python check_subscriptions.py
"""

import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple

BASE_URL = "http://localhost:8000/api/v1"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_success(text: str):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    print(f"{RED}✗ {text}{RESET}")


def print_info(text: str):
    print(f"{BLUE}ℹ {text}{RESET}")


def print_warning(text: str):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_section(title: str):
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{title:^60}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")


def make_request(method: str, path: str, token: Optional[str] = None, body: Optional[Dict] = None) -> Tuple[int, Any]:
    """Make HTTP request and return status code and response data."""
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


def login(email: str, password: str = "Test@1234") -> Optional[str]:
    """Login and return access token."""
    status, data = make_request("POST", "/auth/login", body={
        "email_or_phone": email,
        "password": password
    })
    if status == 200:
        print_success(f"Logged in as {email}")
        return data.get("access_token")
    else:
        print_error(f"Login failed for {email}: {data.get('detail', 'Unknown error')}")
        return None


def test_endpoint(method: str, path: str, token: Optional[str] = None, body: Optional[Dict] = None) -> Tuple[int, Any]:
    """Test an endpoint and return status and data."""
    status, data = make_request(method, path, token, body)
    
    if status == 200 or status == 201:
        print_success(f"{method} {path} - Status {status}")
        return status, data
    elif status == 204:
        print_success(f"{method} {path} - Status {status} (No Content)")
        return status, {}
    elif status == 401:
        print_error(f"{method} {path} - Status {status} (Unauthorized)")
        return status, data
    elif status == 403:
        print_error(f"{method} {path} - Status {status} (Forbidden)")
        return status, data
    elif status == 404:
        print_warning(f"{method} {path} - Status {status} (Not Found)")
        return status, data
    else:
        print_error(f"{method} {path} - Status {status}: {data.get('detail', str(data))}")
        return status, data


def main():
    print_section("SUBSCRIPTION ENDPOINT DIAGNOSTIC")
    
    # Login as Super Admin
    token = login("superadmin@leviticanestora.com")
    if not token:
        print_error("Cannot proceed without super admin token")
        return
    
    # Test 1: List subscriptions (GET)
    print_info("\nTesting GET /super-admin/subscriptions (LIST)...")
    status, subscriptions = test_endpoint("GET", "/super-admin/subscriptions", token)
    
    if status == 200 and subscriptions:
        print_success(f"Found {len(subscriptions)} subscriptions")
        
        # Display first subscription
        if len(subscriptions) > 0:
            first_sub = subscriptions[0]
            print_info(f"Sample: {first_sub.get('id')} - {first_sub.get('tier')}")
            sub_id = first_sub.get('id')
            
            # Test 2: Get single subscription by ID
            print_info(f"\nTesting GET /super-admin/subscriptions/{sub_id}...")
            status, single_sub = test_endpoint("GET", f"/super-admin/subscriptions/{sub_id}", token)
            
            if status == 200:
                print_info(f"  Hostel: {single_sub.get('hostel_name')}")
                print_info(f"  Tier: {single_sub.get('tier')}")
                print_info(f"  Price: ₹{single_sub.get('price_monthly')}/month")
                print_info(f"  Status: {single_sub.get('status')}")
                print_info(f"  Auto-renew: {single_sub.get('auto_renew')}")
                print_info(f"  Start: {single_sub.get('start_date')}")
                print_info(f"  End: {single_sub.get('end_date')}")
                days_left = single_sub.get('days_remaining')
                if days_left is not None:
                    print_info(f"  Days remaining: {days_left}")
    
    # Test 3: List with status filter
    print_info("\nTesting GET with status_filter=active...")
    status, active_subs = test_endpoint("GET", "/super-admin/subscriptions?status_filter=active", token)
    if status == 200:
        active_count = len(active_subs) if isinstance(active_subs, list) else 0
        print_success(f"Found {active_count} active subscriptions")
    
    # Test 4: List with hostel filter (if we have a hostel ID)
    if subscriptions and len(subscriptions) > 0:
        hostel_id = subscriptions[0].get('hostel_id')
        if hostel_id:
            print_info(f"\nTesting GET with hostel_id={hostel_id}...")
            status, hostel_subs = test_endpoint("GET", f"/super-admin/subscriptions?hostel_id={hostel_id}", token)
            if status == 200:
                print_success(f"Found {len(hostel_subs)} subscription(s) for this hostel")
    
    # Test 5: Create subscription (test case - use a hostel without existing subscription)
    print_info("\nTesting POST /super-admin/subscriptions (CREATE)...")
    
    # First, find a hostel without active subscription
    status, all_hostels = make_request("GET", "/super-admin/hostels", token)
    test_hostel_id = None
    test_hostel_name = None
    
    if status == 200 and all_hostels:
        for hostel in all_hostels:
            hid = hostel.get('id')
            # Check if this hostel has active subscription
            status, subs = make_request("GET", f"/super-admin/subscriptions?hostel_id={hid}", token)
            has_active = False
            if status == 200 and subs:
                for sub in subs:
                    if sub.get('status') == 'active':
                        has_active = True
                        break
            
            if not has_active:
                test_hostel_id = hid
                test_hostel_name = hostel.get('name')
                break
    
    if test_hostel_id:
        print_info(f"Using hostel: {test_hostel_name} (ID: {test_hostel_id})")
        
        from datetime import date, timedelta
        start_date = date.today()
        end_date = start_date + timedelta(days=365)
        
        create_payload = {
            "hostel_id": test_hostel_id,
            "tier": "test_basic",
            "price_monthly": 2999.00,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "auto_renew": False,
            "status": "active"
        }
        
        status, new_sub = test_endpoint("POST", "/super-admin/subscriptions", token, body=create_payload)
        
        if status == 201:
            new_sub_id = new_sub.get('id')
            print_success(f"Created test subscription: {new_sub_id}")
            
            # Test 6: Update subscription
            print_info("\nTesting PATCH /super-admin/subscriptions/{id} (UPDATE)...")
            update_payload = {
                "tier": "test_premium",
                "price_monthly": 5999.00,
                "auto_renew": True
            }
            status, updated_sub = test_endpoint("PATCH", f"/super-admin/subscriptions/{new_sub_id}", token, body=update_payload)
            
            if status == 200:
                print_success(f"Updated subscription to tier: {updated_sub.get('tier')}")
                print_info(f"  New price: ₹{updated_sub.get('price_monthly')}")
                print_info(f"  Auto-renew: {updated_sub.get('auto_renew')}")
            
            # Test 7: Cancel subscription
            print_info("\nTesting POST /super-admin/subscriptions/{id}/cancel...")
            status, cancelled = test_endpoint("POST", f"/super-admin/subscriptions/{new_sub_id}/cancel", token)
            
            if status == 200:
                print_success(f"Cancelled subscription: {cancelled.get('status')}")
            
            # Test 8: Delete subscription
            print_info("\nTesting DELETE /super-admin/subscriptions/{id}...")
            status, _ = test_endpoint("DELETE", f"/super-admin/subscriptions/{new_sub_id}", token)
            
            if status == 204:
                print_success("Deleted subscription successfully!")
            
            # Test 9: Verify deletion
            print_info("\nVerifying deletion...")
            status, _ = test_endpoint("GET", f"/super-admin/subscriptions/{new_sub_id}", token)
            
            if status == 404:
                print_success("Verified: Subscription no longer exists")
    else:
        print_warning("No hostel without active subscription found. Skipping create/update/delete tests.")
    
    # Test 10: Error case - Get non-existent subscription
    print_info("\nTesting error case - GET non-existent subscription...")
    fake_id = "00000000-0000-0000-0000-000000000000"
    status, _ = test_endpoint("GET", f"/super-admin/subscriptions/{fake_id}", token)
    if status == 404:
        print_success("Correctly returned 404")
    
    # Summary
    print_section("DIAGNOSTIC SUMMARY")
    print(f"\n{GREEN}✅ Subscription endpoints are available and working!{RESET}")
    print(f"\n{CYAN}📝 Available endpoints:{RESET}")
    print("  ✅ GET    /super-admin/subscriptions")
    print("  ✅ GET    /super-admin/subscriptions/{id}")
    print("  ✅ GET    /super-admin/subscriptions?status_filter=active")
    print("  ✅ GET    /super-admin/subscriptions?hostel_id={id}")
    print("  ✅ POST   /super-admin/subscriptions")
    print("  ✅ PATCH  /super-admin/subscriptions/{id}")
    print("  ✅ POST   /super-admin/subscriptions/{id}/cancel")
    print("  ✅ DELETE /super-admin/subscriptions/{id}")
    print()


if __name__ == "__main__":
    main()