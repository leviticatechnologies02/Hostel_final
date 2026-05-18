# scripts/debug_waitlist.py
import json
import urllib.request
import urllib.error
from datetime import date, timedelta

BASE_URL = "http://localhost:8000/api/v1"

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

# Login
status, data = make_request("POST", "/auth/login", body={
    "email_or_phone": "arun.kapoor@gmail.com",
    "password": "Test@1234"
})
token = data.get("access_token")
print(f"Token obtained: {token[:50]}...")

# Get a room
status, rooms = make_request("GET", "/public/hostels/914ecd63-ab69-41de-85db-c85f8e6c5e0e/rooms", token=token)
print(f"Rooms status: {status}")
if status == 200:
    print(f"Rooms: {json.dumps(rooms[:2], indent=2)}")
    if rooms:
        room_id = rooms[0].get("id")
        print(f"Using room_id: {room_id}")
        
        # Try join waitlist with far future dates
        future_date = (date.today() + timedelta(days=365)).isoformat()
        future_end = (date.today() + timedelta(days=395)).isoformat()
        
        payload = {
            "hostel_id": "914ecd63-ab69-41de-85db-c85f8e6c5e0e",
            "room_id": room_id,
            "booking_mode": "monthly",
            "check_in_date": future_date,
            "check_out_date": future_end
        }
        
        print(f"Payload: {json.dumps(payload, indent=2)}")
        status, data = make_request("POST", "/visitor/waitlist/join", token=token, body=payload)
        print(f"Response status: {status}")
        print(f"Response data: {json.dumps(data, indent=2)}")