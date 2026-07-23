import asyncio
import sys
from pathlib import Path
from datetime import date

# Add parent directory to path to allow importing app module
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.hostel import Hostel
from app.models.room import Room, Bed, BedStatus
from app.models.booking import Booking, BookingStatus, BedStay, BedStayStatus

async def main():
    async with AsyncSessionLocal() as session:
        # Find Blue Sky Boys Hostel
        hostel_query = select(Hostel).where(Hostel.slug == "blue-sky-boys-hostel")
        hostel_result = await session.execute(hostel_query)
        hostel = hostel_result.scalar_one_or_none()
        
        if not hostel:
            print("Hostel 'blue-sky-boys-hostel' not found.")
            return
            
        print(f"Hostel found: {hostel.name} (ID: {hostel.id})")
        
        # Find Room 102
        room_query = select(Room).where(Room.hostel_id == hostel.id, Room.room_number == "102")
        room_result = await session.execute(room_query)
        room = room_result.scalar_one_or_none()
        
        if not room:
            print("Room 102 not found in this hostel.")
            return
            
        print(f"Room found: {room.room_number} (ID: {room.id})")
        
        # Get all beds in Room 102
        beds_query = select(Bed).where(Bed.room_id == room.id)
        beds_result = await session.execute(beds_query)
        beds = beds_result.scalars().all()
        
        print("\nBeds in Room 102:")
        for bed in beds:
            print(f"  - Bed: {bed.bed_number} (ID: {bed.id}), Status: {bed.status.value}")
            
        # Get active bookings in Room 102
        bookings_query = select(Booking).where(
            Booking.room_id == room.id,
            Booking.status.in_([BookingStatus.APPROVED, BookingStatus.CHECKED_IN])
        )
        bookings_result = await session.execute(bookings_query)
        bookings = bookings_result.scalars().all()
        
        print(f"\nActive Bookings for Room 102 ({len(bookings)} found):")
        for booking in bookings:
            print(f"  - Booking: {booking.booking_number}, Guest: {booking.full_name}, Bed ID: {booking.bed_id}, Status: {booking.status.value}, Dates: {booking.check_in_date} to {booking.check_out_date}")
            
        # Get all BedStays for beds in Room 102
        bed_ids = [bed.id for bed in beds]
        stays_query = select(BedStay).where(
            BedStay.bed_id.in_(bed_ids),
            BedStay.status.in_([BedStayStatus.RESERVED, BedStayStatus.ACTIVE])
        )
        stays_result = await session.execute(stays_query)
        stays = stays_result.scalars().all()
        
        print(f"\nActive BedStays for Room 102 ({len(stays)} found):")
        for stay in stays:
            print(f"  - Stay Bed ID: {stay.bed_id}, Status: {stay.status.value}, Dates: {stay.start_date} to {stay.end_date}")
            
        # Call get_available_bed_count to see what room_repository computes
        from app.repositories.room_repository import RoomRepository
        room_repo = RoomRepository(session)
        
        today = date.today()
        tomorrow = today + __import__("datetime").timedelta(days=1)
        available_beds = await room_repo.get_available_bed_count(str(room.id), today, tomorrow)
        print(f"\nAvailable beds count calculated by RoomRepository (today to tomorrow): {available_beds}")

if __name__ == "__main__":
    asyncio.run(main())
