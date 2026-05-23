# scripts/test_fixed_endpoints.py
#!/usr/bin/env python3
"""
Test fixed endpoints: leave-request and read-status
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta

BASE_URL = "http://localhost:8000/api/v1"

GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'
YELLOW = '\033[93m'


def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ {text}{RESET}")

def print_section(title):
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{title:^60}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")

def make_request(method, path, token=None, body=None):
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

def login(email, password="Test@1234"):
    status, data = make_request("POST", "/auth/login", body={
        "email_or_phone": email,
        "password": password
    })
    if status == 200:
        print_success(f"Logged in as {email}")
        return data.get("access_token")
    else:
        print_error(f"Login failed: {data.get('detail', 'Unknown')}")
        return None

def test_read_status():
    print_section("TESTING: GET /student/notices/read-status")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print_error("Login failed")
        return False
    
    status, data = make_request("GET", "/student/notices/read-status", token=token)
    
    if status == 200:
        print_success(f"Read-status endpoint works!")
        print_info(f"Read notice IDs: {data}")
        return True
    else:
        print_error(f"Failed: {status} - {data.get('detail', 'Unknown')}")
        return False

def test_leave_request():
    print_section("TESTING: POST /student/leave-request")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print_error("Login failed")
        return False
    
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()
    
    payload = {
        "from_date": tomorrow,
        "to_date": next_week,
        "reason": "Medical leave"
    }
    
    print_info(f"Payload: {json.dumps(payload)}")
    
    status, data = make_request("POST", "/student/leave-request", token=token, body=payload)
    
    if status == 201:
        print_success(f"Leave request created!")
        print_info(f"Reference: {data.get('reference')}")
        print_info(f"Status: {data.get('status')}")
        return True
    else:
        print_error(f"Failed: {status} - {data.get('detail', 'Unknown')}")
        return False

def test_visitor_read_status():
    print_section("TESTING: GET /visitor/notices/read-status")
    
    token = login("arun.kapoor@gmail.com")
    if not token:
        print_error("Login failed")
        return False
    
    status, data = make_request("GET", "/visitor/notices/read-status", token=token)
    
    if status == 200:
        print_success(f"Visitor read-status endpoint works!")
        print_info(f"Read notice IDs: {data}")
        return True
    else:
        print_error(f"Failed: {status} - {data.get('detail', 'Unknown')}")
        return False

def test_mark_notice_read():
    print_section("TESTING: Mark notice as read")
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print_error("Login failed")
        return False
    
    # First get a notice
    status, notices = make_request("GET", "/student/notices/paginated?page=1&per_page=5", token=token)
    if status != 200:
        print_error("Could not fetch notices")
        return False
    
    items = notices.get("items", [])
    if not items:
        print_info("No notices found to mark as read")
        return True
    
    notice_id = items[0].get("id")
    print_info(f"Marking notice {notice_id} as read")
    
    status, data = make_request("POST", f"/student/notices/{notice_id}/read", token=token)
    
    if status == 200:
        print_success(f"Notice marked as read!")
        return True
    else:
        print_error(f"Failed: {status}")
        return False

def run_all_tests():
    print_section("FIXED ENDPOINTS TEST SUITE")
    
    results = []
    
    # Test read-status endpoints
    results.append(("Student Read Status", test_read_status()))
    results.append(("Visitor Read Status", test_visitor_read_status()))
    
    # Test marking notice as read
    results.append(("Mark Notice Read", test_mark_notice_read()))
    
    # Test leave request
    results.append(("Leave Request", test_leave_request()))
    
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status} - {name}")
    
    print(f"\n  {BOLD}Passed:{RESET} {passed}")
    print(f"  {BOLD}Failed:{RESET} {failed}")
    
    if failed == 0:
        print(f"\n{GREEN}{BOLD}✅ All fixed endpoints are working!{RESET}")
    else:
        print(f"\n{RED}{BOLD}❌ Some endpoints still failing.{RESET}")
        print(f"\n{YELLOW}Make sure to apply the fixes to:{RESET}")
        print("  1. app/api/v1/student/routes.py - create_leave_request")
        print("  2. app/api/v1/student/routes.py - get_read_notice_ids")
        print("  3. app/api/v1/visitor/routes.py - get_visitor_read_notice_ids")
        print("  4. app/services/notice_service.py - get_user_read_notices")

if __name__ == "__main__":
    run_all_tests()