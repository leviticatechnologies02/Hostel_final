#!/usr/bin/env python3
"""
Student Login & Role Test Script
Diagnoses why students are redirected to visitor pages.

Run: python test_student_login.py
"""

import json
import urllib.request
import urllib.error
import asyncio
import asyncpg
from datetime import datetime
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
    """Login and return full response"""
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


def test_student_endpoint(token: str, endpoint: str, name: str) -> bool:
    """Test if student can access an endpoint"""
    status, data = make_request("GET", endpoint, token=token)
    
    if status == 200:
        print_success(f"✅ Student can access {name}")
        return True
    elif status == 403:
        print_error(f"❌ Student CANNOT access {name} (403 Forbidden)")
        print_info(f"   Response: {data.get('detail', 'No detail')}")
        return False
    else:
        print_warning(f"⚠️ {name} returned status {status}")
        return False


async def check_database_role(email: str, db_url: str) -> tuple[str, bool]:
    """Check user role directly in database"""
    try:
        conn = await asyncpg.connect(db_url)
        result = await conn.fetchrow(
            "SELECT role, is_active FROM users WHERE email = $1",
            email
        )
        await conn.close()
        
        if result:
            return result['role'], result['is_active']
        return None, False
    except Exception as e:
        print_error(f"Database query failed: {e}")
        return None, False


async def update_database_role(email: str, new_role: str, db_url: str) -> bool:
    """Update user role in database"""
    try:
        conn = await asyncpg.connect(db_url)
        await conn.execute(
            "UPDATE users SET role = $1 WHERE email = $2",
            new_role, email
        )
        await conn.close()
        print_success(f"Updated {email} role to {new_role}")
        return True
    except Exception as e:
        print_error(f"Failed to update role: {e}")
        return False


def main():
    print_section("STUDENT LOGIN DIAGNOSTIC")
    
    # Test student emails (from seed data)
    student_emails = [
        "hemant.pawade.lev044@levitica.in",
        "abhilash.gurrampally.lev029@levitica.in",
        "arun.kapoor@gmail.com",  # This is a visitor, for comparison
    ]
    
    results = {}
    
    for email in student_emails:
        print_section(f"Testing: {email}")
        
        # 1. Try to login
        login_response = login(email)
        
        if not login_response:
            print_error(f"Cannot login as {email}")
            continue
        
        token = login_response.get("access_token")
        role_from_login = login_response.get("role")
        user_id = login_response.get("user_id")
        
        print_info(f"Role from login response: {role_from_login}")
        print_info(f"User ID: {user_id}")
        
        # 2. Test which endpoints student can access
        print_info("\nTesting endpoint access:")
        
        # Student endpoints (should work)
        student_endpoints = [
            ("/student/profile", "Student Profile"),
            ("/student/bookings", "Student Bookings"),
            ("/student/payments", "Student Payments"),
            ("/student/attendance", "Student Attendance"),
            ("/student/complaints", "Student Complaints"),
            ("/student/notices/paginated", "Student Notices"),
            ("/student/mess-menu", "Student Mess Menu"),
        ]
        
        student_access = []
        for endpoint, name in student_endpoints:
            can_access = test_student_endpoint(token, endpoint, name)
            student_access.append(can_access)
        
        # Visitor endpoints (should also work for students)
        print_info("\nTesting visitor endpoints (should work for students):")
        visitor_endpoints = [
            ("/visitor/profile", "Visitor Profile"),
            ("/visitor/bookings", "Visitor Bookings"),
            ("/visitor/favorites", "Visitor Favorites"),
        ]
        
        for endpoint, name in visitor_endpoints:
            test_student_endpoint(token, endpoint, name)
        
        # Admin endpoints (should NOT work)
        print_info("\nTesting admin endpoints (should fail):")
        status, _ = make_request("GET", "/admin/dashboard", token=token)
        if status == 403:
            print_success("✅ Student correctly blocked from admin dashboard")
        else:
            print_error(f"❌ Student accessed admin dashboard (status {status})")
        
        # Store results
        results[email] = {
            "role_from_login": role_from_login,
            "student_endpoint_access": all(student_access) if student_access else False,
            "can_access_count": sum(student_access)
        }
    
    # Summary
    print_section("SUMMARY")
    
    print("\nResults:")
    for email, data in results.items():
        status_icon = "✅" if data["student_endpoint_access"] else "❌"
        print(f"  {status_icon} {email}")
        print(f"     Role in token: {data['role_from_login']}")
        print(f"     Student endpoints accessible: {data['can_access_count']}/7")
    
    # Recommendations
    print_section("RECOMMENDATIONS")
    
    if any(not r["student_endpoint_access"] for r in results.values()):
        print(f"\n{RED}❌ Students cannot access student endpoints!{RESET}\n")
        print("Possible causes and fixes:")
        print("")
        print("1. DATABASE ROLE IS INCORRECT")
        print("   - Student users have 'visitor' role in database")
        print("   - Run: UPDATE users SET role = 'student' WHERE email LIKE '%@levitica.in';")
        print("")
        print("2. TOKEN NOT REFRESHED AFTER ROLE CHANGE")
        print("   - When a visitor becomes a student, old tokens remain valid")
        print("   - Add token revocation in StudentService.check_in_from_booking()")
        print("")
        print("3. JWT TOKEN CONTAINS OLD ROLE")
        print("   - The JWT payload doesn't include role, so it always queries DB")
        print("   - Check that get_current_user() is fetching fresh role from DB")
        print("")
        print("QUICK FIX:")
        print("   UPDATE users SET role = 'student' WHERE role = 'visitor' AND email LIKE '%@levitica.in';")
    else:
        print(f"\n{GREEN}✅ Students can access student endpoints correctly!{RESET}")
        print("\nIf still redirecting to visitor pages, check frontend routing:")
        print("  - Does the frontend check `user.role === 'student'`?")
        print("  - Is localStorage being cleared after role change?")
        print("  - Are you using the token from login response (not stored old token)?")


if __name__ == "__main__":
    # Ask for database URL if needed
    import os
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:Kiran$1234@localhost:5432/stayease_dev')
    
    async def run_db_check():
        print_section("DATABASE ROLE CHECK")
        
        for email in ["hemant.pawade.lev044@levitica.in", "abhilash.gurrampally.lev029@levitica.in"]:
            role, is_active = await check_database_role(email, db_url)
            if role:
                status = "✅" if role == "student" else "❌"
                print(f"  {status} {email}: role={role}, active={is_active}")
                
                if role != "student":
                    print_warning(f"  {email} has role '{role}' - should be 'student'!")
                    response = input(f"  Fix now? (y/n): ").strip().lower()
                    if response == 'y':
                        await update_database_role(email, "student", db_url)
            else:
                print_error(f"  User not found: {email}")
    
    # Run async DB check
    asyncio.run(run_db_check())
    
    # Run main tests
    main()