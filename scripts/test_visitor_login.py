# scripts/test_visitor_login.py
#!/usr/bin/env python3
"""
Test Visitor Login and Role Assignment
Run: python scripts/test_visitor_login.py
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000/api/v1"

def make_request(method, path, body=None, token=None):
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

def test_visitor_login():
    print("\n" + "="*60)
    print("TESTING VISITOR LOGIN")
    print("="*60)
    
    # Test 1: Login as visitor
    print("\n1. Login as Visitor (arun.kapoor@gmail.com)")
    status, data = make_request("POST", "/auth/login", body={
        "email_or_phone": "arun.kapoor@gmail.com",
        "password": "Test@1234"
    })
    
    if status == 200:
        print(f"✅ Visitor login successful!")
        print(f"   User ID: {data.get('user_id')}")
        print(f"   Role: {data.get('role')}")
        print(f"   Token: {data.get('access_token')[:50]}...")
        visitor_token = data.get('access_token')
        
        # Test visitor profile
        status, profile = make_request("GET", "/visitor/profile", token=visitor_token)
        if status == 200:
            print(f"✅ Visitor profile accessible")
            print(f"   Name: {profile.get('full_name')}")
            print(f"   Email: {profile.get('email')}")
        else:
            print(f"❌ Visitor profile failed: {status}")
        
        # Test student profile (should FAIL for visitor)
        status, profile = make_request("GET", "/student/profile", token=visitor_token)
        if status == 403:
            print(f"✅ Visitor correctly blocked from student profile (403)")
        else:
            print(f"⚠️ Visitor got status {status} on student profile (expected 403)")
    else:
        print(f"❌ Visitor login failed: {status} - {data.get('detail', 'Unknown')}")
        visitor_token = None
    
    return visitor_token

def test_student_login():
    print("\n" + "="*60)
    print("TESTING STUDENT LOGIN")
    print("="*60)
    
    # Test student emails from seed data
    student_emails = [
        "hemant.pawade.lev044@levitica.in",
        "abhilash.gurrampally.lev029@levitica.in",
        "arun.kapoor@gmail.com",  # This is actually visitor, not student
    ]
    
    student_token = None
    
    for email in student_emails:
        print(f"\n2. Login as: {email}")
        status, data = make_request("POST", "/auth/login", body={
            "email_or_phone": email,
            "password": "Test@1234"
        })
        
        if status == 200:
            role = data.get('role')
            print(f"   ✅ Login successful! Role: {role}")
            
            if role == "student":
                student_token = data.get('access_token')
                print(f"   ✅ Student token obtained")
                
                # Test student profile
                status, profile = make_request("GET", "/student/profile", token=student_token)
                if status == 200:
                    print(f"   ✅ Student profile accessible")
                    print(f"      Name: {profile.get('full_name')}")
                    print(f"      Student #: {profile.get('student_number')}")
                else:
                    print(f"   ❌ Student profile failed: {status} - {profile.get('detail', 'Unknown')}")
                
                # Test visitor profile (should be accessible - students can use visitor endpoints)
                status, profile = make_request("GET", "/visitor/profile", token=student_token)
                if status == 200:
                    print(f"   ✅ Student can access visitor profile (expected)")
                else:
                    print(f"   ⚠️ Student cannot access visitor profile: {status}")
            else:
                print(f"   ⚠️ Login successful but role is '{role}', not 'student'")
        else:
            print(f"   ❌ Login failed: {status} - {data.get('detail', 'Unknown')}")
    
    return student_token

def check_database_roles():
    print("\n" + "="*60)
    print("CHECKING DATABASE ROLES")
    print("="*60)
    
    try:
        import asyncpg
        import asyncio
        
        async def check():
            conn = await asyncpg.connect(
                "postgresql://postgres:Kiran$1234@localhost:5432/stayease_dev"
            )
            
            # Check student emails
            rows = await conn.fetch("""
                SELECT email, role 
                FROM users 
                WHERE email LIKE '%@levitica.in' OR email = 'arun.kapoor@gmail.com'
                ORDER BY email
            """)
            
            print("\nUser roles in database:")
            for row in rows:
                role_marker = "✅" if row['role'] == 'student' else "⚠️"
                print(f"  {role_marker} {row['email']}: {row['role']}")
            
            # Count students vs visitors
            counts = await conn.fetch("""
                SELECT role, COUNT(*) 
                FROM users 
                GROUP BY role
            """)
            
            print("\nRole counts:")
            for row in counts:
                print(f"  {row['role']}: {row['count']}")
            
            await conn.close()
        
        asyncio.run(check())
    except Exception as e:
        print(f"⚠️ Could not check database: {e}")
        print("   Make sure PostgreSQL is running and credentials are correct")

def test_student_endpoints(student_token):
    if not student_token:
        print("\n❌ No student token available - skipping student endpoint tests")
        return
    
    print("\n" + "="*60)
    print("TESTING STUDENT ENDPOINTS")
    print("="*60)
    
    endpoints = [
        ("GET", "/student/profile", "Student Profile"),
        ("GET", "/student/bookings", "Student Bookings"),
        ("GET", "/student/payments", "Student Payments"),
        ("GET", "/student/attendance", "Student Attendance"),
        ("GET", "/student/notices/paginated", "Student Notices"),
        ("GET", "/student/mess-menu", "Student Mess Menu"),
        ("GET", "/student/complaints", "Student Complaints"),
    ]
    
    for method, path, name in endpoints:
        status, data = make_request(method, path, token=student_token)
        if status == 200:
            count = len(data) if isinstance(data, list) else 1
            print(f"✅ {name}: OK (status {status}, {count} items)")
        elif status == 403:
            print(f"❌ {name}: FORBIDDEN (status 403) - Role issue!")
        else:
            print(f"⚠️ {name}: Status {status}")

def main():
    print("\n" + "="*70)
    print("  VISITOR/STUDENT LOGIN DIAGNOSTIC")
    print("="*70)
    
    # Check database first
    check_database_roles()
    
    # Test visitor login
    visitor_token = test_visitor_login()
    
    # Test student login
    student_token = test_student_login()
    
    # Test student endpoints if we have a token
    test_student_endpoints(student_token)
    
    print("\n" + "="*70)
    print("  DIAGNOSTIC COMPLETE")
    print("="*70)
    
    if student_token:
        print("\n✅ Student token obtained successfully")
    else:
        print("\n❌ Could not obtain student token")
        print("\nPossible issues:")
        print("  1. Student users don't have 'student' role in database")
        print("  2. Student password is incorrect (should be 'Test@1234')")
        print("  3. Student accounts weren't created during seeding")
        print("\nFix: Run 'python -m scripts.seed_data --clean' to regenerate student accounts")

if __name__ == "__main__":
    main()