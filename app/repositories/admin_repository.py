from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, update
from app.models.hostel import Hostel, SupervisorHostelMapping
from app.models.room import Bed, BedStatus
from app.models.room import Room
from app.models.student import Student
from app.models.user import User, UserRole
from app.models.operations import AttendanceRecord


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_rooms(self, hostel_id: str) -> list[Room]:
        result = await self.session.execute(select(Room).where(Room.hostel_id == hostel_id))
        return list(result.scalars().all())

    async def create_room(self, room: Room) -> Room:
        self.session.add(room)
        await self.session.flush()
        return room

    async def list_beds(self, room_id: str) -> list[Bed]:
        result = await self.session.execute(select(Bed).where(Bed.room_id == room_id))
        return list(result.scalars().all())

    async def create_bed(self, bed: Bed) -> Bed:
        self.session.add(bed)
        await self.session.flush()
        return bed

    async def get_bed_by_id(self, bed_id: str) -> Bed | None:
        result = await self.session.execute(select(Bed).where(Bed.id == bed_id))
        return result.scalar_one_or_none()


    async def get_hostel_by_id(self, hostel_id: str) -> Hostel | None:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Hostel)
            .options(selectinload(Hostel.amenities), selectinload(Hostel.images))
            .where(Hostel.id == hostel_id)
        )
        return result.scalar_one_or_none()

    async def list_hostels_by_ids(self, hostel_ids: list[str]) -> list[Hostel]:
        if not hostel_ids:
            return []
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Hostel)
            .options(selectinload(Hostel.images))          # ← eager-load images
            .where(Hostel.id.in_(hostel_ids))
            .order_by(Hostel.created_at.desc())
        )
        return list(result.scalars().all())


    async def list_supervisors(self, hostel_id: str) -> list[User]:
        result = await self.session.execute(
            select(User)
            .join(SupervisorHostelMapping, SupervisorHostelMapping.supervisor_id == User.id)
            .where(
                SupervisorHostelMapping.hostel_id == hostel_id,
                User.role == UserRole.SUPERVISOR,
            )
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_supervisor(self, supervisor: User) -> User:
        self.session.add(supervisor)
        await self.session.flush()
        return supervisor

    async def assign_supervisor_to_hostel(self, supervisor_id: str, hostel_id: str, assigned_by: str) -> None:
        self.session.add(
            SupervisorHostelMapping(
                supervisor_id=supervisor_id,
                hostel_id=hostel_id,
                assigned_by=assigned_by,
            )
        )
        await self.session.flush()

    async def get_student_by_id(self, student_id: str) -> Student | None:
        """Get student by ID"""
        result = await self.session.execute(select(Student).where(Student.id == student_id))
        return result.scalar_one_or_none()



    async def list_attendance(self, hostel_id: str) -> list[AttendanceRecord]:
        result = await self.session.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.hostel_id == hostel_id)
            .order_by(AttendanceRecord.date.desc(), AttendanceRecord.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_room_by_id(self, room_id: str) -> Room | None:
        result = await self.session.execute(select(Room).where(Room.id == room_id))
        return result.scalar_one_or_none()

    async def delete_room(self, room: Room) -> None:
        await self.session.delete(room)
        await self.session.flush()


    async def get_supervisor_by_id(self, supervisor_id: str) -> User | None:
        """Get supervisor by ID"""
        result = await self.session.execute(
            select(User).where(
                User.id == supervisor_id,
                User.role == UserRole.SUPERVISOR
            )
        )
        return result.scalar_one_or_none()

    async def update_supervisor(self, supervisor: User, update_data: dict) -> User:
        """Update supervisor details"""
        for field, value in update_data.items():
            if value is not None and hasattr(supervisor, field):
                setattr(supervisor, field, value)
        await self.session.flush()
        return supervisor

    async def delete_supervisor_mappings(self, supervisor_id: str) -> None:
        """Delete all hostel mappings for a supervisor"""
        from app.models.hostel import SupervisorHostelMapping
        result = await self.session.execute(
            select(SupervisorHostelMapping).where(
                SupervisorHostelMapping.supervisor_id == supervisor_id
            )
        )
        mappings = result.scalars().all()
        for mapping in mappings:
            await self.session.delete(mapping)
        await self.session.flush()

    async def delete_supervisor(self, supervisor: User) -> None:
        """Delete supervisor user"""
        await self.session.delete(supervisor)
        await self.session.flush()

    async def get_bed_by_room_and_number(self, room_id: str, bed_number: str) -> Bed | None:
        """Check if a bed with given number already exists in the room."""
        result = await self.session.execute(
            select(Bed).where(
                Bed.room_id == room_id,
                Bed.bed_number == bed_number
            )
        )
        return result.scalar_one_or_none()


    async def list_students(self, hostel_id: str) -> list[dict]:
        from app.models.room import Room, Bed
        from app.models.booking import Booking
        result = await self.session.execute(
            select(
                Student,
                User.full_name,
                User.email,
                User.phone,
                User.profile_picture_url,
                Room.room_number,
                Bed.bed_number,
                Booking.full_name,
                Booking.gender,
                Booking.date_of_birth,
            )
            .join(User, User.id == Student.user_id)
            .outerjoin(Room, Room.id == Student.room_id)
            .outerjoin(Bed, Bed.id == Student.bed_id)
            .outerjoin(Booking, Booking.id == Student.booking_id)
            .where(Student.hostel_id == hostel_id)
            .order_by(Student.check_in_date.desc())
        )
        rows = result.all()
        
        students_list = []
        for row in rows:
            # Unpack the row
            (s, user_name, email, phone, profile_picture_url, 
            room_number, bed_number, booking_name, gender, date_of_birth) = row
            
            student_dict = self._student_to_dict(
                s=s,
                full_name=booking_name or user_name,
                email=email,
                phone=phone,
                profile_picture_url=profile_picture_url,
                room_number=room_number,
                bed_number=bed_number,
                gender=gender,
                date_of_birth=date_of_birth,
            )
            students_list.append(student_dict)
        
        return students_list


    async def list_students_by_hostel_ids(self, hostel_ids: list[str]) -> list[dict]:
        if not hostel_ids:
            return []
        from app.models.room import Room, Bed
        from app.models.booking import Booking
        result = await self.session.execute(
            select(
                Student,
                User.full_name,
                User.email,
                User.phone,
                User.profile_picture_url,
                Room.room_number,
                Bed.bed_number,
                Booking.full_name,
                Booking.gender,
                Booking.date_of_birth,
            )
            .join(User, User.id == Student.user_id)
            .outerjoin(Room, Room.id == Student.room_id)
            .outerjoin(Bed, Bed.id == Student.bed_id)
            .outerjoin(Booking, Booking.id == Student.booking_id)
            .where(Student.hostel_id.in_(hostel_ids))
            .order_by(Student.check_in_date.desc(), Student.created_at.desc())
        )
        rows = result.all()
        
        students_list = []
        for row in rows:
            # Unpack the row
            (s, user_name, email, phone, profile_picture_url, 
            room_number, bed_number, booking_name, gender, date_of_birth) = row
            
            student_dict = self._student_to_dict(
                s=s,
                full_name=booking_name or user_name,
                email=email,
                phone=phone,
                profile_picture_url=profile_picture_url,
                room_number=room_number,
                bed_number=bed_number,
                gender=gender,
                date_of_birth=date_of_birth,
            )
            students_list.append(student_dict)
        
        return students_list


    @staticmethod
    def _student_to_dict(
        s: Student,
        full_name: str | None,
        email: str | None,
        phone: str | None,
        profile_picture_url: str | None = None,
        room_number: str | None = None,
        bed_number: str | None = None,
        gender: str | None = None,
        date_of_birth: date | None = None,
    ) -> dict:
        return {
            "id": str(s.id),
            "user_id": str(s.user_id),
            "hostel_id": str(s.hostel_id),
            "room_id": str(s.room_id),
            "bed_id": str(s.bed_id),
            "booking_id": str(s.booking_id),
            "student_number": s.student_number,
            "check_in_date": str(s.check_in_date) if s.check_in_date else None,
            "check_out_date": str(s.check_out_date) if s.check_out_date else None,
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "profile_picture_url": profile_picture_url,
            "room_number": room_number,
            "bed_number": bed_number,
            "gender": gender,
            "date_of_birth": str(date_of_birth) if date_of_birth else None,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }