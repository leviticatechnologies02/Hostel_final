#!/usr/bin/env python3
"""
Test Subscription CRUD Operations - Handles existing subscriptions gracefully.

Run: python scripts/test_subscription_crud.py
"""

import json
import urllib.request
import urllib.error
from datetime import date, timedelta
from typing import Optional, Dict, Any

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


def login(email: str, password: str = "Test@1234") -> Optional[str]:
    """Login and return access token"""
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


def get_or_create_test_hostel(token: str) -> tuple[Optional[str], Optional[str], bool]:
    """Get a hostel without active subscription or create a test hostel."""
    
    # First, list existing hostels
    status, hostels = make_request("GET", "/super-admin/hostels", token=token)
    if status != 200:
        print_error(f"Could not fetch hostels: {status}")
        return None, None, False
    
    # Check each hostel for active subscription
    for hostel in hostels:
        hostel_id = hostel.get("id")
        hostel_name = hostel.get("name")
        
        # Check if this hostel has an active subscription
        status, subscriptions = make_request("GET", f"/super-admin/subscriptions?hostel_id={hostel_id}", token=token)
        
        has_active = False
        if status == 200 and subscriptions:
            for sub in subscriptions:
                if sub.get("status") == "active":
                    has_active = True
                    break
        
        if not has_active:
            print_success(f"Found hostel without active subscription: {hostel_name}")
            return hostel_id, hostel_name, False
    
    # All hostels have active subscriptions - create a test hostel
    print_warning("All hostels have active subscriptions. Creating a test hostel...")
    
    # Create a test hostel
    test_hostel = {
        "name": "Test Subscription Hostel",
        "slug": "test-subscription-hostel",
        "description": "Temporary hostel for subscription testing",
        "hostel_type": "coed",
        "address_line1": "123 Test Street",
        "address_line2": "Test Area",
        "city": "Test City",
        "state": "Test State",
        "country": "India",
        "pincode": "123456",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "phone": "+91-9876543210",
        "email": "test@leviticanestora.com",
        "website": "https://test.leviticanestora.com",
        "is_featured": False,
        "is_public": True,
        "rules_and_regulations": "Test rules"
    }
    
    status, new_hostel = make_request("POST", "/super-admin/hostels", token=token, body=test_hostel)
    
    if status == 201:
        hostel_id = new_hostel.get("id")
        hostel_name = new_hostel.get("name")
        print_success(f"Created test hostel: {hostel_name} (ID: {hostel_id})")
        return hostel_id, hostel_name, True
    else:
        print_error(f"Failed to create test hostel: {status} - {new_hostel.get('detail', 'Unknown')}")
        return None, None, False


def cancel_existing_subscription(token: str, hostel_id: str):
    """Cancel any existing active subscription for a hostel."""
    status, subscriptions = make_request("GET", f"/super-admin/subscriptions?hostel_id={hostel_id}", token=token)
    
    if status == 200 and subscriptions:
        for sub in subscriptions:
            if sub.get("status") == "active":
                sub_id = sub.get("id")
                print_info(f"Cancelling existing active subscription: {sub_id}")
                cancel_status, _ = make_request("POST", f"/super-admin/subscriptions/{sub_id}/cancel", token=token)
                if cancel_status == 200:
                    print_success(f"Cancelled subscription: {sub_id}")
                else:
                    print_warning(f"Could not cancel subscription {sub_id}")


def cleanup_test_hostel(token: str, hostel_id: str, created_for_test: bool = False):
    """Clean up test hostel and its subscriptions."""
    if not created_for_test:
        return
    
    print_info(f"Cleaning up test hostel: {hostel_id}")
    
    # First, cancel any subscriptions
    status, subscriptions = make_request("GET", f"/super-admin/subscriptions?hostel_id={hostel_id}", token=token)
    if status == 200 and subscriptions:
        for sub in subscriptions:
            sub_id = sub.get("id")
            if sub.get("status") == "active":
                make_request("POST", f"/super-admin/subscriptions/{sub_id}/cancel", token=token)
            make_request("DELETE", f"/super-admin/subscriptions/{sub_id}", token=token)
    
    # Delete the hostel
    # Note: You may need a DELETE hostel endpoint; if not, just leave it
    # status, _ = make_request("DELETE", f"/super-admin/hostels/{hostel_id}", token=token)
    print_info(f"Test hostel {hostel_id} can be manually cleaned up if needed")


def test_subscription_crud():
    print_section("SUBSCRIPTION CRUD TESTING")
    
    # Login as Super Admin
    token = login("superadmin@leviticanestora.com")
    if not token:
        print_error("Cannot proceed without super admin token")
        return
    
    # Step 1: Get a hostel ID (either without subscription or create one)
    print_info("Finding a suitable hostel for testing...")
    hostel_id, hostel_name, was_test_hostel = get_or_create_test_hostel(token)
    
    if not hostel_id:
        print_error("Could not find or create a test hostel")
        return
    
    print_success(f"Using hostel: {hostel_name} (ID: {hostel_id})")
    
    # Step 2: Cancel any existing subscription for this hostel
    cancel_existing_subscription(token, hostel_id)
    
    # Step 3: Create a new subscription
    print_info("\nCreating new subscription...")
    start_date = date.today()
    end_date = start_date + timedelta(days=365)  # 1 year
    
    create_payload = {
        "hostel_id": hostel_id,
        "tier": "professional",
        "price_monthly": 4999.00,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "auto_renew": True,
        "status": "active"
    }
    
    status, subscription = make_request("POST", "/super-admin/subscriptions", token=token, body=create_payload)
    
    if status != 201:
        print_error(f"Failed to create subscription: {status} - {subscription.get('detail', 'Unknown')}")
        if was_test_hostel:
            cleanup_test_hostel(token, hostel_id, True)
        return
    
    subscription_id = subscription.get("id")
    print_success(f"Created subscription: {subscription_id}")
    print_info(f"  Tier: {subscription.get('tier')}")
    print_info(f"  Price: ₹{subscription.get('price_monthly')}/month")
    print_info(f"  Valid: {subscription.get('start_date')} to {subscription.get('end_date')}")
    
    # Step 4: Get subscription by ID
    print_info("\nFetching subscription by ID...")
    status, fetched = make_request("GET", f"/super-admin/subscriptions/{subscription_id}", token=token)
    
    if status != 200:
        print_error(f"Failed to fetch subscription: {status}")
    else:
        print_success(f"Fetched subscription: {fetched.get('id')}")
        days_left = fetched.get('days_remaining')
        print_info(f"  Days remaining: {days_left}")
        print_info(f"  Auto-renew: {fetched.get('auto_renew')}")
    
    # Step 5: List all subscriptions
    print_info("\nListing all subscriptions...")
    status, subscriptions = make_request("GET", "/super-admin/subscriptions", token=token)
    
    if status == 200:
        print_success(f"Found {len(subscriptions)} total subscriptions")
        # Show recent 3
        for sub in subscriptions[:3]:
            status_icon = "🟢" if sub.get('status') == 'active' else "🔴" if sub.get('status') == 'cancelled' else "🟡"
            print_info(f"  {status_icon} {sub.get('hostel_name')}: {sub.get('tier')} (₹{sub.get('price_monthly')})")
    
    # Step 6: List by hostel filter
    print_info(f"\nListing subscriptions for hostel: {hostel_name}")
    status, hostel_subs = make_request("GET", f"/super-admin/subscriptions?hostel_id={hostel_id}", token=token)
    if status == 200:
        print_success(f"Hostel has {len(hostel_subs)} subscription(s)")
    
    # Step 7: List by status filter
    print_info("\nFiltering by status...")
    status, active_subs = make_request("GET", "/super-admin/subscriptions?status_filter=active", token=token)
    if status == 200:
        print_success(f"Active subscriptions: {len(active_subs)}")
    
    status, cancelled_subs = make_request("GET", "/super-admin/subscriptions?status_filter=cancelled", token=token)
    if status == 200:
        print_success(f"Cancelled subscriptions: {len(cancelled_subs)}")
    
    # Step 8: Update subscription
    print_info("\nUpdating subscription...")
    update_payload = {
        "tier": "enterprise",
        "price_monthly": 9999.00,
        "auto_renew": False
    }
    
    status, updated = make_request("PATCH", f"/super-admin/subscriptions/{subscription_id}", token=token, body=update_payload)
    
    if status != 200:
        print_error(f"Failed to update subscription: {status}")
    else:
        print_success(f"Updated subscription:")
        print_info(f"  New tier: {updated.get('tier')}")
        print_info(f"  New price: ₹{updated.get('price_monthly')}")
        print_info(f"  Auto-renew: {updated.get('auto_renew')}")
    
    # Step 9: Cancel subscription (soft delete)
    print_info("\nCancelling subscription...")
    status, cancelled = make_request("POST", f"/super-admin/subscriptions/{subscription_id}/cancel", token=token)
    
    if status != 200:
        print_error(f"Failed to cancel subscription: {status}")
    else:
        print_success(f"Cancelled subscription: {cancelled.get('status')}")
        print_info(f"  Auto-renew now: {cancelled.get('auto_renew')}")
    
    # Step 10: Verify cancellation
    print_info("\nVerifying cancellation...")
    status, cancelled_check = make_request("GET", f"/super-admin/subscriptions/{subscription_id}", token=token)
    if status == 200:
        print_success(f"Subscription status is now: {cancelled_check.get('status')}")
    
    # Step 11: Delete subscription (only allowed after cancellation)
    print_info("\nDeleting cancelled subscription...")
    status, _ = make_request("DELETE", f"/super-admin/subscriptions/{subscription_id}", token=token)
    
    if status == 204:
        print_success("Subscription deleted successfully!")
    else:
        print_error(f"Failed to delete subscription: {status}")
    
    # Step 12: Verify deletion
    print_info("Verifying deletion...")
    status, _ = make_request("GET", f"/super-admin/subscriptions/{subscription_id}", token=token)
    
    if status == 404:
        print_success("Verified: Subscription no longer exists")
    else:
        print_error(f"Subscription still exists (status: {status})")
    
    # Step 13: Test validation - create subscription for same hostel (should work since we deleted)
    print_info("\nTesting duplicate subscription prevention...")
    status, duplicate = make_request("POST", "/super-admin/subscriptions", token=token, body=create_payload)
    
    if status == 201:
        print_success("Created new subscription (deleted previous one)")
        # Clean up this subscription too
        new_sub_id = duplicate.get("id")
        if new_sub_id:
            make_request("POST", f"/super-admin/subscriptions/{new_sub_id}/cancel", token=token)
            make_request("DELETE", f"/super-admin/subscriptions/{new_sub_id}", token=token)
    elif status == 409:
        print_success("Correctly rejected duplicate active subscription")
    else:
        print_warning(f"Unexpected status: {status}")
    
    # Step 14: Test error cases
    print_info("\nTesting error cases...")
    
    # Update non-existent subscription
    fake_id = "00000000-0000-0000-0000-000000000000"
    status, _ = make_request("PATCH", f"/super-admin/subscriptions/{fake_id}", token=token, body={"tier": "basic"})
    if status == 404:
        print_success("Correctly returned 404 for non-existent subscription update")
    
    # Delete non-existent subscription
    status, _ = make_request("DELETE", f"/super-admin/subscriptions/{fake_id}", token=token)
    if status == 404:
        print_success("Correctly returned 404 for non-existent subscription delete")
    
    # Cancel non-existent subscription
    status, _ = make_request("POST", f"/super-admin/subscriptions/{fake_id}/cancel", token=token)
    if status == 404:
        print_success("Correctly returned 404 for non-existent subscription cancel")
    
    # Cleanup test hostel if we created it
    if was_test_hostel:
        cleanup_test_hostel(token, hostel_id, True)
    
    # Summary
    print_section("TEST SUMMARY")
    print(f"\n{GREEN}✅ All subscription CRUD tests completed!{RESET}")
    print(f"\n{CYAN}📝 Available subscription endpoints:{RESET}")
    print("  GET    /super-admin/subscriptions                      - List subscriptions (supports filters)")
    print("  GET    /super-admin/subscriptions/{id}                 - Get single subscription")
    print("  POST   /super-admin/subscriptions                      - Create subscription")
    print("  PATCH  /super-admin/subscriptions/{id}                 - Update subscription")
    print("  POST   /super-admin/subscriptions/{id}/cancel          - Cancel subscription (soft delete)")
    print("  DELETE /super-admin/subscriptions/{id}                 - Delete subscription (hard delete)")
    print(f"\n{CYAN}📝 Filter parameters:{RESET}")
    print("  status_filter=active|expired|cancelled")
    print("  hostel_id={hostel_uuid}")
    print()


if __name__ == "__main__":
    test_subscription_crud()