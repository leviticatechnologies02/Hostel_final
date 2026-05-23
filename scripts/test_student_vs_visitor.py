# scripts/test_student_vs_visitor.py
import requests

BASE = "http://localhost:8000/api/v1"

# Login as student
resp = requests.post(f"{BASE}/auth/login", json={
    "email_or_phone": "hemant.pawade.lev044@levitica.in",
    "password": "Test@1234"
})
token = resp.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

print("=== Student Access Test ===")

# Student-specific endpoint (should work)
r = requests.get(f"{BASE}/student/profile", headers=headers)
print(f"GET /student/profile: {r.status_code} - {'✅' if r.status_code == 200 else '❌'}")

# Visitor endpoint (should also work - by design)
r = requests.get(f"{BASE}/visitor/profile", headers=headers)
print(f"GET /visitor/profile: {r.status_code} - {'✅' if r.status_code == 200 else '❌'}")

# Try to access admin endpoint (should FAIL)
r = requests.get(f"{BASE}/admin/dashboard", headers=headers)
print(f"GET /admin/dashboard: {r.status_code} - {'✅' if r.status_code == 403 else '❌'}")