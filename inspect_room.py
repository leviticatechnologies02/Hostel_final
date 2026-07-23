import asyncio
import psycopg2

DATABASE_URL = "postgres://stayease_db_0hw4_user:0L7DvsoMZ4ff88BYqohgiceUJITTSmJG@dpg-d7kaci4m0tmc73aeivm0-a.oregon-postgres.render.com/stayease_db_0hw4?sslmode=require"

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Find Blue Sky Boys Hostel ID
    cur.execute("SELECT id, name FROM hostels WHERE slug = 'blue-sky-boys-hostel' OR name ILIKE '%blue sky%'")
    hostel = cur.fetchone()
    if not hostel:
        print("Hostel not found.")
        return
    hostel_id, hostel_name = hostel
    print(f"Hostel: {hostel_name} (ID: {hostel_id})")

    # Find Room 102 ID
    cur.execute("SELECT id, room_number FROM rooms WHERE hostel_id = %s AND room_number = '102'", (hostel_id,))
    room = cur.fetchone()
    if not room:
        print("Room 102 not found.")
        return
    room_id, room_number = room
    print(f"Room: {room_number} (ID: {room_id})")

    # Find all beds in Room 102
    cur.execute("SELECT id, bed_number, status FROM beds WHERE room_id = %s", (room_id,))
    beds = cur.fetchall()
    print("\nBeds in Room 102:")
    for bed in beds:
        print(f"  Bed ID: {bed[0]}, Number: {bed[1]}, Status: {bed[2]}")

    # Find all active bookings/stays for Room 102
    cur.execute("""
        SELECT b.booking_number, b.full_name, b.status, b.check_in_date, b.check_out_date, b.bed_id, bd.bed_number
        FROM bookings b
        JOIN beds bd ON b.bed_id = bd.id
        WHERE b.room_id = %s AND b.status IN ('approved', 'checked_in')
    """, (room_id,))
    bookings = cur.fetchall()
    print("\nActive Bookings for Room 102:")
    for b in bookings:
        print(f"  Number: {b[0]}, Guest: {b[1]}, Status: {b[2]}, Dates: {b[3]} to {b[4]}, Bed: {b[6]} (ID: {b[5]})")

    # Check BedStay entries for Room 102 beds
    cur.execute("""
        SELECT bs.id, bs.bed_id, bd.bed_number, bs.booking_number, bs.status, bs.start_date, bs.end_date
        FROM (
            SELECT id, bed_id, booking_id, status, start_date, end_date,
                   (SELECT booking_number FROM bookings WHERE id = booking_id) as booking_number
            FROM bed_stays
        ) bs
        JOIN beds bd ON bs.bed_id = bd.id
        WHERE bd.room_id = %s AND bs.status IN ('reserved', 'active')
    """, (room_id,))
    stays = cur.fetchall()
    print("\nActive Bed Stays for Room 102:")
    for s in stays:
        print(f"  Stay ID: {s[0]}, Bed: {s[2]}, Booking: {s[3]}, Status: {s[4]}, Dates: {s[5]} to {s[6]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
