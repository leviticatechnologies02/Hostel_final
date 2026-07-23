# scripts/verify_duplicate_check.py
import json
import urllib.request

def make_request(method, path, token=None, body=None):
    url = f"http://localhost:8000/api/v1{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# Login
status, data = make_request("POST", "/auth/login", body={
    "email_or_phone": "superadmin@leviticanestora.com",
    "password": "Test@1234"
})
token = data.get("access_token")

# Try to create duplicate admin
status, data = make_request("POST", "/super-admin/admins", token=token, body={
    "email": "admin1@leviticanestora.com",  # Already exists!
    "phone": "9999999999",
    "full_name": "Duplicate Admin",
    "password": "Test@1234"
})

print(f"\nStatus: {status}")
print(f"Response: {data}")
print(f"\n✅ Email uniqueness is {'WORKING' if status == 409 else 'BROKEN'}!")