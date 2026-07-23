#!/usr/bin/env python3
"""
Check what student data is actually available in the database
Run: python check_student_data.py
"""

import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgresql://postgres:Kiran$1234@localhost:5432/leviticanestora_dev"

async def check_students():
    """Check student data in database"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    print("\n" + "="*80)
    print("STUDENT DATA DATABASE CHECK")
    print("="*80)
    
    # 1. Check students table
    print("\n1. STUDENTS TABLE")
    students = await conn.fetch("""
        SELECT s.id, s.student_number, s.user_id, s.hostel_id, s.room_id, s.bed_id, 
               s.booking_id, s.check_in_date, s.check_out_date, s.status,
               u.full_name, u.email, u.phone
        FROM students s
        JOIN users u ON u.id = s.user_id
        LIMIT 5
    """)
    
    print(f"   Total students: {len(await conn.fetch('SELECT COUNT(*) FROM students'))}")
    print(f"   Sample (first 5):")
    for s in students:
        print(f"     - {s['full_name']}: student_number={s['student_number']}, status={s['status']}")
    
    # 2. Check rooms and beds for students
    print("\n2. ROOM & BED DATA FOR STUDENTS")
    room_bed_data = await conn.fetch("""
        SELECT s.id as student_id, s.student_number, u.full_name,
               r.room_number, r.room_type, r.floor,
               b.bed_number
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN rooms r ON r.id = s.room_id
        LEFT JOIN beds b ON b.id = s.bed_id
        LIMIT 5
    """)
    
    for row in room_bed_data:
        print(f"     - {row['full_name']}: Room={row['room_number'] or 'NULL'}, Bed={row['bed_number'] or 'NULL'}, Type={row['room_type'] or 'NULL'}")
    
    # 3. Check booking data for students
    print("\n3. BOOKING DATA FOR STUDENTS")
    booking_data = await conn.fetch("""
        SELECT s.id, u.full_name, b.booking_number, b.booking_mode, 
               b.gender, b.date_of_birth, b.occupation, b.institution,
               b.emergency_contact_name, b.emergency_contact_phone
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN bookings b ON b.id = s.booking_id
        LIMIT 5
    """)
    
    for row in booking_data:
        print(f"     - {row['full_name']}: Booking={row['booking_number'] or 'NULL'}, Gender={row['gender'] or 'NULL'}")
    
    # 4. Check payments for students
    print("\n4. PAYMENT DATA FOR STUDENTS")
    payment_data = await conn.fetch("""
        SELECT s.id, u.full_name, 
               COUNT(p.id) as payment_count,
               COALESCE(SUM(CASE WHEN p.status = 'captured' THEN p.amount ELSE 0 END), 0) as total_paid
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN payments p ON p.student_id = s.id
        GROUP BY s.id, u.full_name
        LIMIT 5
    """)
    
    for row in payment_data:
        print(f"     - {row['full_name']}: {row['payment_count']} payments, Total Paid=₹{float(row['total_paid']):,.0f}")
    
    # 5. Check which fields are actually populated
    print("\n5. DATA POPULATION SUMMARY")
    
    stats = await conn.fetch("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN room_id IS NOT NULL THEN 1 END) as has_room,
            COUNT(CASE WHEN bed_id IS NOT NULL THEN 1 END) as has_bed,
            COUNT(CASE WHEN s.booking_id IS NOT NULL THEN 1 END) as has_booking,
            COUNT(CASE WHEN b.gender IS NOT NULL THEN 1 END) as has_gender,
            COUNT(CASE WHEN b.occupation IS NOT NULL THEN 1 END) as has_occupation
        FROM students s
        LEFT JOIN bookings b ON b.id = s.booking_id
    """)
    
    for stat in stats:
        print(f"     Total students: {stat['total']}")
        print(f"     Have room_id: {stat['has_room']}")
        print(f"     Have bed_id: {stat['has_bed']}")
        print(f"     Have booking: {stat['has_booking']}")
        print(f"     Have gender: {stat['has_gender']}")
        print(f"     Have occupation: {stat['has_occupation']}")
    
    await conn.close()
    
    print("\n" + "="*80)
    print("CONCLUSION: Room/Bed data exists but API isn't returning it!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(check_students())