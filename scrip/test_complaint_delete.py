"""Test Complaint Delete API"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_complaint_operations():
    print("\n" + "="*60)
    print("Testing Complaint CRUD Operations")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # Step 1: Login as admin
        print("\n📝 Step 1: Login as Admin")
        resp = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email_or_phone": "admin1@leviticanestora.com", "password": "Test@1234"}
        )
        
        if resp.status_code != 200:
            print(f"✗ Login failed: {resp.status_code}")
            return
        
        data = resp.json()
        token = data.get("access_token")
        hostel_ids = data.get("hostel_ids", [])
        
        if not hostel_ids:
            print("✗ No hostel assigned to admin")
            return
        
        hostel_id = hostel_ids[0]
        print(f"✓ Logged in as Admin")
        print(f"  Hostel ID: {hostel_id}")
        
        # Step 2: Check existing complaints
        print("\n📝 Step 2: List existing complaints")
        resp = await client.get(
            f"{BASE_URL}/admin/hostels/{hostel_id}/complaints",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if resp.status_code == 200:
            complaints = resp.json()
            print(f"✓ Found {len(complaints)} complaints")
            
            for c in complaints[:3]:
                print(f"  - ID: {c.get('id')[:8]}... | Status: {c.get('status')} | Title: {c.get('title')[:30]}")
            
            # Step 3: Delete a complaint if exists
            if complaints:
                complaint_id = complaints[0]["id"]
                print(f"\n📝 Step 3: Delete complaint {complaint_id[:8]}...")
                
                resp = await client.delete(
                    f"{BASE_URL}/admin/complaints/{complaint_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if resp.status_code == 204:
                    print(f"✓ Complaint deleted successfully!")
                else:
                    print(f"✗ Delete failed: {resp.status_code} - {resp.text}")
            else:
                print("\n⚠️ No complaints to delete")
                
            # Step 4: Create a test complaint
            print("\n📝 Step 4: Create test complaint")
            
            # First get a student ID
            student_resp = await client.get(
                f"{BASE_URL}/admin/hostels/{hostel_id}/students",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if student_resp.status_code == 200:
                students = student_resp.json()
                if students:
                    student_id = students[0].get("id") if isinstance(students[0], dict) else students[0].id
                    
                    # Create complaint via student endpoint
                    # First login as student to create complaint
                    student_login = await client.post(
                        f"{BASE_URL}/auth/login",
                        json={"email_or_phone": "student@leviticanestora.com", "password": "Test@1234"}
                    )
                    
                    if student_login.status_code == 200:
                        student_token = student_login.json().get("access_token")
                        
                        create_resp = await client.post(
                            f"{BASE_URL}/student/complaints",
                            json={
                                "category": "maintenance",
                                "title": "Test Complaint for Delete",
                                "description": "This is a test complaint to verify delete functionality",
                                "priority": "medium"
                            },
                            headers={"Authorization": f"Bearer {student_token}"}
                        )
                        
                        if create_resp.status_code == 201:
                            new_complaint = create_resp.json()
                            new_complaint_id = new_complaint.get("id")
                            print(f"✓ Created test complaint: {new_complaint_id[:8]}...")
                            
                            # Step 5: Delete the new complaint
                            print(f"\n📝 Step 5: Delete test complaint")
                            delete_resp = await client.delete(
                                f"{BASE_URL}/admin/complaints/{new_complaint_id}",
                                headers={"Authorization": f"Bearer {token}"}
                            )
                            
                            if delete_resp.status_code == 204:
                                print(f"✓ Test complaint deleted successfully!")
                            else:
                                print(f"✗ Delete failed: {delete_resp.status_code}")
                        else:
                            print(f"✗ Failed to create complaint: {create_resp.status_code}")
                    else:
                        print(f"✗ Student login failed")
                else:
                    print("✗ No students found")
            else:
                print(f"✗ Failed to get students: {student_resp.status_code}")
        else:
            print(f"✗ Failed to list complaints: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(test_complaint_operations())