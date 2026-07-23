import json, urllib.request, urllib.error

BASE = "http://localhost:8000/api/v1"

def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {}
        except Exception:
            return e.code, {}

_, sup_login = req("POST", "/auth/login", {"email_or_phone": "supervisor1@leviticanestora.com", "password": "Test@1234"})
sup_token = sup_login.get("access_token", "")

tests = [
    ("GET", "/supervisor/maintenance"),
    ("GET", "/supervisor/notices"),
    ("GET", "/supervisor/mess-menu"),
]

print("\n[9 continued] Supervisor tail tests")
for method, path in tests:
    s, d = req(method, path, token=sup_token)
    count = len(d) if isinstance(d, list) else d
    result = "[PASS]" if s == 200 else "[FAIL]"
    print(f"  {result} {path} — status={s}, data={count}")

print("\n[ALL DONE]")
