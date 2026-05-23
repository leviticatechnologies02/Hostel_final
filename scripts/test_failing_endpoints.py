# test_failing_endpoints.py
#!/usr/bin/env python3
"""
Test specific failing endpoints with detailed output
Run: python scripts/test_failing_endpoints.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta

BASE_URL = "http://localhost:8000/api/v1"

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


def make_request(method: str, path: str, token: str = None, body: dict = None):
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


def login(email: str, password: str = "Test@1234"):
    status, data = make_request("POST", "/auth/login", body={
        "email_or_phone": email,
        "password": password
    })
    if status == 200:
        return data.get("access_token")
    return None


def test_notice_read_status():
    print("\n" + "="*60)
    print("TESTING: GET /student/notices/read-status")
    print("="*60)
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print("❌ Failed to login")
        return
    
    status, data = make_request("GET", "/student/notices/read-status", token=token)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)[:500]}")
    
    if status == 200:
        print(f"✅ Endpoint works! Found {len(data)} read notices")
    else:
        print(f"❌ Endpoint failed")
        # Try to get more info
        print("\nTrying to get notices first...")
        status2, notices = make_request("GET", "/student/notices/paginated?page=1&per_page=1", token=token)
        if status2 == 200:
            print(f"Notices endpoint works: {notices.get('total', 0)} notices found")
        else:
            print(f"Notices endpoint also failed: {status2}")


def test_leave_request():
    print("\n" + "="*60)
    print("TESTING: POST /student/leave-request")
    print("="*60)
    
    token = login("hemant.pawade.lev044@levitica.in")
    if not token:
        print("❌ Failed to login")
        return
    
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()
    
    payload = {
        "from_date": tomorrow,
        "to_date": next_week,
        "reason": "Vacation leave"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    status, data = make_request("POST", "/student/leave-request", token=token, body=payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if status == 201:
        print("✅ Leave request created successfully!")
    else:
        print("❌ Leave request failed")
        # Try with different dates
        print("\nTrying with different date format...")
        payload2 = {
            "from_date": str(tomorrow),
            "to_date": str(next_week),
            "reason": "Test"
        }
        status2, data2 = make_request("POST", "/student/leave-request", token=token, body=payload2)
        print(f"Status: {status2}")


if __name__ == "__main__":
    test_notice_read_status()
    test_leave_request()