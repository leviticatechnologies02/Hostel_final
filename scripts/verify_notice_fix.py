#!/usr/bin/env python3
"""
Verify Notice Date Fields Fix
Run: python scripts/verify_notice_fix.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

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


def make_request(method: str, path: str, token: str = None, body: dict = None) -> tuple:
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


def login(email: str, password: str = "Test@1234") -> str:
    status, data = make_request("POST", "/auth/login", body={
        "email_or_phone": email,
        "password": password
    })
    if status == 200:
        return data.get("access_token")
    print_error(f"Login failed: {data.get('detail', 'Unknown')}")
    return None


def test_student_notice_dates():
    """Test student notice date fields"""
    print_section("VERIFY STUDENT NOTICE DATE FIELDS")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        return
    
    status, data = make_request("GET", "/student/notices/paginated?page=1&per_page=20", token=token)
    
    if status != 200:
        print_error(f"Failed: {status}")
        return
    
    items = data.get("items", [])
    print_info(f"Found {len(items)} notices")
    
    passed = 0
    failed = 0
    
    for notice in items[:5]:
        title = notice.get("title", "Unknown")[:50]
        print_info(f"\n📝 {title}")
        
        # Check created_at
        created = notice.get("created_at")
        if created:
            print_success(f"  ✓ created_at: {created}")
            passed += 1
        else:
            print_error(f"  ✗ created_at: MISSING")
            failed += 1
        
        # Check publish_at
        publish = notice.get("publish_at")
        if publish is not None:
            print_success(f"  ✓ publish_at: {publish}")
            passed += 1
        else:
            # publish_at can be None (not set) - that's fine
            print_info(f"  ℹ publish_at: None (not set)")
        
        # Check expires_at
        expires = notice.get("expires_at")
        if expires is not None:
            print_success(f"  ✓ expires_at: {expires}")
            passed += 1
        else:
            print_info(f"  ℹ expires_at: None (not set)")
    
    print_section("RESULT")
    
    if failed == 0:
        print_success(f"✅ PASSED: All notices have created_at field!")
        print_info("Note: publish_at/expires_at are optional - they appear only when set")
    else:
        print_error(f"❌ FAILED: {failed} notices missing required fields")


def test_admin_notice_dates():
    """Test admin notice endpoints also work"""
    print_section("VERIFY ADMIN NOTICE DATE FIELDS")
    
    token = login("admin1@stayease.com")
    if not token:
        return
    
    status, data = make_request("GET", "/admin/notices/platform?page=1&per_page=10", token=token)
    
    if status != 200:
        print_error(f"Failed: {status}")
        return
    
    items = data.get("items", [])
    print_info(f"Found {len(items)} platform notices")
    
    for notice in items[:3]:
        title = notice.get("title", "Unknown")[:50]
        print_info(f"\n📝 {title}")
        
        created = notice.get("created_at")
        if created:
            print_success(f"  ✓ created_at: {created}")
        else:
            print_error(f"  ✗ created_at: MISSING")
        
        publish = notice.get("publish_at")
        if publish:
            print_success(f"  ✓ publish_at: {publish}")
        elif publish is None:
            print_info(f"  ℹ publish_at: None")
        
        expires = notice.get("expires_at")
        if expires:
            print_success(f"  ✓ expires_at: {expires}")
        elif expires is None:
            print_info(f"  ℹ expires_at: None")


def test_create_notice_with_dates():
    """Test creating a notice with all date fields"""
    print_section("CREATE NOTICE WITH ALL DATE FIELDS")
    
    token = login("admin1@stayease.com")
    if not token:
        return
    
    # First get a hostel ID
    status, hostels = make_request("GET", "/admin/my-hostels", token=token)
    if status != 200 or not hostels:
        print_error("No hostels found")
        return
    
    hostel_id = hostels[0].get("id")
    from datetime import datetime, timedelta
    
    now = datetime.now()
    future = now + timedelta(days=30)
    
    notice_data = {
        "hostel_id": hostel_id,
        "title": f"Fix Verification Notice {now.strftime('%H:%M:%S')}",
        "content": "Testing date fields after fix",
        "notice_type": "general",
        "priority": "medium",
        "is_published": True,
        "publish_at": now.isoformat(),
        "expires_at": future.isoformat()
    }
    
    status, data = make_request("POST", f"/admin/hostels/{hostel_id}/notices", token=token, body=notice_data)
    
    if status == 201:
        print_success("Notice created successfully!")
        print_info(f"  ID: {data.get('id')}")
        print_info(f"  created_at: {data.get('created_at')}")
        print_info(f"  publish_at: {data.get('publish_at')}")
        print_info(f"  expires_at: {data.get('expires_at')}")
        
        # Verify all date fields are present
        if data.get('created_at') and data.get('publish_at') and data.get('expires_at'):
            print_success("✅ All date fields present in response!")
            return data.get('id')
        else:
            print_error("❌ Some date fields missing")
    else:
        print_error(f"Failed: {status}")


if __name__ == "__main__":
    print_section("VERIFY NOTICE DATE FIELDS FIX")
    test_create_notice_with_dates()
    test_student_notice_dates()
    test_admin_notice_dates()j