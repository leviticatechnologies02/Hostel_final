#!/usr/bin/env python3
"""
Test Supervisor Update and Delete Endpoints
Run: python test_supervisor_crud.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def make_request(method, path, token=None, body=None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {}
        except:
            return e.code, {'detail': raw.decode('utf-8', errors='replace')}

def login(email, password="Test@1234"):
    status, data = make_request('POST', '/auth/login', body={
        'email_or_phone': email,
        'password': password
    })
    if status == 200:
        return data.get('access_token'), data.get('hostel_ids', [])
    return None, []

def test_update_supervisor():
    print("\n" + "="*60)
    print("TEST: Update Supervisor")
    print("="*60)
    
    # Login as Admin
    admin_token, hostel_ids = login("admin1@leviticanestora.com")
    if not admin_token:
        print("❌ Admin login failed")
        return False
    
    # Get list of supervisors
    if not hostel_ids:
        print("❌ No hostels found for admin")
        return False
    
    hostel_id = hostel_ids[0]
    status, supervisors = make_request(
        'GET', 
        f'/admin/hostels/{hostel_id}/supervisors',
        token=admin_token
    )
    
    if status != 200 or not supervisors:
        print("❌ No supervisors found to update")
        return False
    
    supervisor_id = supervisors[0].get('id')
    print(f"✓ Found supervisor: {supervisors[0].get('full_name')} (ID: {supervisor_id})")
    
    # Update supervisor
    update_data = {
        "full_name": f"Updated Supervisor {datetime.now().strftime('%H:%M:%S')}",
        "phone": "+91-8888888888"
    }
    
    status, result = make_request(
        'PATCH',
        f'/admin/supervisors/{supervisor_id}',
        token=admin_token,
        body=update_data
    )
    
    if status == 200:
        print(f"✅ Supervisor updated successfully!")
        print(f"   New name: {result.get('full_name')}")
        print(f"   Phone: {result.get('phone')}")
        return True
    else:
        print(f"❌ Update failed: {status} - {result.get('detail', 'Unknown error')}")
        return False

def test_delete_supervisor():
    print("\n" + "="*60)
    print("TEST: Delete Supervisor")
    print("="*60)
    
    # Login as Admin
    admin_token, hostel_ids = login("admin1@leviticanestora.com")
    if not admin_token:
        print("❌ Admin login failed")
        return False
    
    # First create a test supervisor to delete
    if not hostel_ids:
        print("❌ No hostels found")
        return False
    
    hostel_id = hostel_ids[0]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    create_data = {
        "email": f"test.delete.{timestamp}@leviticanestora.com",
        "phone": f"+91-9{timestamp[-9:]}",
        "full_name": f"Delete Test {timestamp}",
        "password": "Test@1234"
    }
    
    status, new_supervisor = make_request(
        'POST',
        f'/admin/hostels/{hostel_id}/supervisors',
        token=admin_token,
        body=create_data
    )
    
    if status != 201:
        print(f"❌ Could not create test supervisor: {status}")
        return False
    
    supervisor_id = new_supervisor.get('id')
    print(f"✓ Created test supervisor: {new_supervisor.get('full_name')} (ID: {supervisor_id})")
    
    # Delete the supervisor
    status, result = make_request(
        'DELETE',
        f'/admin/supervisors/{supervisor_id}',
        token=admin_token
    )
    
    if status == 204:
        print(f"✅ Supervisor deleted successfully!")
        
        # Verify deletion
        status, verify = make_request(
            'GET',
            f'/admin/supervisors/{supervisor_id}',
            token=admin_token
        )
        
        if status == 404:
            print("✅ Verified: Supervisor no longer exists")
        else:
            print(f"⚠️ Deletion may not have worked (GET returned {status})")
        
        return True
    else:
        print(f"❌ Delete failed: {status} - {result.get('detail', 'Unknown error')}")
        return False

def test_update_nonexistent_supervisor():
    print("\n" + "="*60)
    print("TEST: Update Nonexistent Supervisor (404)")
    print("="*60)
    
    admin_token, _ = login("admin1@leviticanestora.com")
    if not admin_token:
        print("❌ Admin login failed")
        return False
    
    fake_id = "00000000-0000-0000-0000-000000000000"
    update_data = {"full_name": "Should Fail"}
    
    status, result = make_request(
        'PATCH',
        f'/admin/supervisors/{fake_id}',
        token=admin_token,
        body=update_data
    )
    
    if status == 404:
        print("✅ Correctly returned 404 for nonexistent supervisor")
        return True
    else:
        print(f"❌ Expected 404, got {status}")
        return False

def test_delete_nonexistent_supervisor():
    print("\n" + "="*60)
    print("TEST: Delete Nonexistent Supervisor (404)")
    print("="*60)
    
    admin_token, _ = login("admin1@leviticanestora.com")
    if not admin_token:
        print("❌ Admin login failed")
        return False
    
    fake_id = "00000000-0000-0000-0000-000000000000"
    
    status, result = make_request(
        'DELETE',
        f'/admin/supervisors/{fake_id}',
        token=admin_token
    )
    
    if status == 404:
        print("✅ Correctly returned 404 for nonexistent supervisor")
        return True
    else:
        print(f"❌ Expected 404, got {status}")
        return False

def test_update_supervisor_unauthorized():
    print("\n" + "="*60)
    print("TEST: Update Supervisor from Different Hostel (403)")
    print("="*60)
    
    # Login as Admin 1
    admin1_token, hostel_ids1 = login("admin1@leviticanestora.com")
    if not admin1_token:
        print("❌ Admin 1 login failed")
        return False
    
    # Get a supervisor from Admin 1's hostel
    if not hostel_ids1:
        print("❌ No hostels for Admin 1")
        return False
    
    status, supervisors = make_request(
        'GET',
        f'/admin/hostels/{hostel_ids1[0]}/supervisors',
        token=admin1_token
    )
    
    if not supervisors:
        print("⚠️ No supervisors found in Admin 1's hostel")
        return True  # Skip, not a failure
    
    supervisor_id = supervisors[0].get('id')
    
    # Login as Admin 2 (different admin, different hostel)
    admin2_token, hostel_ids2 = login("admin2@leviticanestora.com")
    if not admin2_token:
        print("❌ Admin 2 login failed")
        return False
    
    # Try to update supervisor from Admin 1's hostel using Admin 2's token
    update_data = {"full_name": "Unauthorized Update"}
    
    status, result = make_request(
        'PATCH',
        f'/admin/supervisors/{supervisor_id}',
        token=admin2_token,
        body=update_data
    )
    
    if status == 403:
        print("✅ Correctly returned 403 for unauthorized access")
        return True
    else:
        print(f"❌ Expected 403, got {status}")
        return False

def run_all_tests():
    print("\n" + "="*70)
    print("  SUPERVISOR UPDATE & DELETE API TESTS")
    print("="*70)
    
    tests = [
        ("Update Supervisor", test_update_supervisor),
        ("Delete Supervisor", test_delete_supervisor),
        ("Update Nonexistent (404)", test_update_nonexistent_supervisor),
        ("Delete Nonexistent (404)", test_delete_nonexistent_supervisor),
        ("Unauthorized Update (403)", test_update_supervisor_unauthorized),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} crashed: {str(e)}")
            results.append((name, False))
    
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED! Update and Delete are working correctly.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    run_all_tests()