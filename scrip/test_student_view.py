#!/usr/bin/env python3
"""
Diagnostic script to check student data directly
Run: python check_students_direct.py
"""

import asyncio
import asyncpg
from datetime import datetime

async def check_students():
    # Connect directly to database
    conn = await asyncpg.connect(
        "postgresql://postgres:Kiran$1234@localhost:5432/leviticanestora_dev"
    )
    
    print("\n" + "=" * 80)
    print("STUDENT DATA DIAGNOSTIC")
    print("=" * 80)
    
    # 1. Count students
    count = await conn.fetchval("SELECT COUNT(*) FROM students")
    print(f"\n📊 Total students: {count}")
    
    # 2. Get all students with basic info
    print("\n📋 BASIC STUDENT INFO:")
    print("-" * 80)
    
    rows = await conn.fetch("""
        SELECT 
            s.id,
            s.student_number,
            s.status,
            s.check_in_date,
            s.check_out_date,
            u.full_name,
            u.email,
            u.phone,
            r.room_number,
            b.bed_number,
            bk.booking_number,
            bk.gender,
            bk.occupation,
            bk.institution,
            h.name as hostel_name,
            h.city as hostel_city
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN rooms r ON r.id = s.room_id
        LEFT JOIN beds b ON b.id = s.bed_id
        LEFT JOIN bookings bk ON bk.id = s.booking_id
        LEFT JOIN hostels h ON h.id = s.hostel_id
        LIMIT 5
    """)
    
    for row in rows:
        print(f"\n  {'─' * 76}")
        print(f"  🆔 ID: {row['id']}")
        print(f"  📛 Name: {row['full_name']}")
        print(f"  📧 Email: {row['email']}")
        print(f"  📞 Phone: {row['phone']}")
        print(f"  🔢 Student #: {row['student_number']}")
        print(f"  🏠 Room: {row['room_number'] or 'N/A'}")
        print(f"  🛏️ Bed: {row['bed_number'] or 'N/A'}")
        print(f"  📅 Check-in: {row['check_in_date']}")
        print(f"  📅 Check-out: {row['check_out_date'] or 'Active'}")
        print(f"  ⚥ Gender: {row['gender'] or 'N/A'}")
        print(f"  💼 Occupation: {row['occupation'] or 'N/A'}")
        print(f"  🏫 Institution: {row['institution'] or 'N/A'}")
        print(f"  🏨 Hostel: {row['hostel_name']}")
        print(f"  📍 City: {row['hostel_city']}")
        print(f"  📊 Status: {row['status']}")
        print(f"  🎫 Booking #: {row['booking_number']}")
    
    # 3. Check payments
    print("\n" + "-" * 80)
    print("💰 PAYMENT SUMMARY:")
    print("-" * 80)
    
    payments = await conn.fetch("""
        SELECT 
            s.id as student_id,
            u.full_name,
            COUNT(p.id) as payment_count,
            SUM(CASE WHEN p.status = 'captured' THEN p.amount ELSE 0 END) as total_paid
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN payments p ON p.student_id = s.id
        GROUP BY s.id, u.full_name
        LIMIT 5
    """)
    
    for p in payments:
        print(f"  📛 {p['full_name']}: {p['payment_count']} payments, Total: ₹{float(p['total_paid'] or 0):,.0f}")
    
    await conn.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check_students())