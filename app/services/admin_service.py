"""
Admin service – hostel management operations.
"""
from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.models.booking import Booking, BookingMode, BookingStatus, BedStay, BedStayStatus
from app.models.hostel import AdminHostelMapping, Hostel, HostelStatus
from app.models.operations import Complaint, MaintenanceRequest
from app.models.payment import Payment
from app.models.room import Bed, BedStatus, Room, RoomType
from app.models.student import Student, StudentStatus
from app.models.user import User, UserRole
from app.repositories.admin_repository import AdminRepository
from app.schemas import hostel
from app.schemas.room import RoomCreateRequest, RoomUpdateRequest, BedCreateRequest, BedUpdateRequest
from app.schemas.hostel import HostelUpdateRequest
from app.schemas.admin import SupervisorCreateRequest
from app.services.complaint_service import ComplaintService
from app.services.maintenance_service import MaintenanceService
from app.services.payment_service import PaymentService
from app.services.subscription_validator import SubscriptionValidator
from app.repositories.room_repository import RoomRepository
from sqlalchemy import or_, select, update, delete, func

class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AdminRepository(session)
        self.complaints = ComplaintService(session)
        self.maintenance = MaintenanceService(session)
        self.payments = PaymentService(session)

    def map_hostel_to_response(self, hostel: Hostel) -> dict:
        return {
            "id": str(hostel.id),
            "name": hostel.name,
            "slug": hostel.slug,
            "description": hostel.description,
            "city": hostel.city,
            "state": hostel.state,
            "hostel_type": hostel.hostel_type.value,
            "status": hostel.status.value,
            "is_public": hostel.is_public,
            "is_featured": hostel.is_featured,
            "created_at": hostel.created_at,
            "updated_at": hostel.updated_at,

            "rating": 0.0,
            "total_reviews": 0,
            "starting_price": 0.0,
            "starting_daily_price": 0.0,
            "starting_monthly_price": 0.0,
            "available_beds": 0,

            "address_line1": hostel.address_line1,
            "address_line2": hostel.address_line2,
            "country": hostel.country,
            "pincode": hostel.pincode,
            "latitude": hostel.latitude,
            "longitude": hostel.longitude,
            "phone": hostel.phone,
            "email": hostel.email,
            "website": hostel.website,
            "rules_and_regulations": hostel.rules_and_regulations,

            "amenities": [a.name for a in hostel.amenities],

            "images": [
                {
                    "id": str(img.id),
                    "url": img.url,
                    "thumbnail_url": img.thumbnail_url,
                    "is_primary": img.is_primary,
                }
                for img in hostel.images
            ],
        }

    async def list_hostels(self, hostel_ids: list[str]) -> list[dict]:
        """List hostels by IDs, including their images."""
        hostels = await self.repository.list_hostels_by_ids(hostel_ids)
        return [
            {
                "id": str(h.id),
                "name": h.name,
                "slug": h.slug,
                "description": h.description,
                "city": h.city,
                "state": h.state,
                "hostel_type": h.hostel_type.value,
                "status": h.status.value,
                "is_public": h.is_public,
                "is_featured": h.is_featured,
                "is_active": h.is_active,
                "is_verified": h.is_verified,
                "status_reason": h.status_reason,
                "created_at": h.created_at,
                "updated_at": h.updated_at,
                "rating": 0.0,
                "total_reviews": 0,
                "starting_price": 0.0,
                "starting_daily_price": 0.0,
                "starting_monthly_price": 0.0,
                "available_beds": 0,
                "images": [
                    {
                        "id": str(img.id),
                        "url": img.url,
                        "thumbnail_url": img.thumbnail_url,
                        "caption": img.caption,
                        "is_primary": img.is_primary,
                        "sort_order": img.sort_order,
                    }
                    for img in h.images
                ],
            }
            for h in hostels
        ]


    async def get_hostel(self, hostel_id: str) -> dict | None:
        hostel = await self.repository.get_hostel_by_id(hostel_id)

        if not hostel:
            return None
        return self.map_hostel_to_response(hostel)

    async def update_hostel(self, hostel_id: str, payload: HostelUpdateRequest):
        hostel = await self.repository.get_hostel_by_id(hostel_id)

        if hostel is None:
            raise HTTPException(status_code=404, detail="Hostel not found.")

        update_data = payload.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(hostel, field, value)

        await self.session.commit()
        await self.session.refresh(hostel)

        # ✅ FIX
        return self.map_hostel_to_response(hostel)

    async def list_rooms(self, hostel_id: str):
        rooms = await self.repository.list_rooms(hostel_id)

        for room in rooms:
            room.available_beds = await RoomRepository.get_available_bed_count(
                self=self,
                room_id=room.id,
                start_date=date.today(),
                end_date=date.today()
            )

        return rooms

    async def create_room(self, hostel_id: str, payload: RoomCreateRequest) -> Room:
        """
        Create a new room in a hostel and automatically create its beds.
        
        Fixed bug: bed_number now uses instance attribute room.room_number 
        instead of class attribute Room.room_number which created invalid SQL.
        """
        # Create the room
        room = Room(
            hostel_id=hostel_id,
            room_number=payload.room_number,
            floor=payload.floor,
            room_type=payload.room_type.upper().replace("-", "_") if payload.room_type else None,
            total_beds=payload.total_beds,
            daily_rent=payload.daily_rent,
            monthly_rent=payload.monthly_rent,
            security_deposit=payload.security_deposit,
            dimensions=payload.dimensions,
            is_active=True,
        )
        self.session.add(room)
        await self.session.flush()  # ← Obtain room.id
        
        # ✅ FIX: Use instance attribute room.room_number (string value)
        # instead of class attribute Room.room_number (SQL column expression)
        for i in range(room.total_beds):
            bed = Bed(
                hostel_id=hostel_id,
                room_id=str(room.id),
                bed_number=f"{room.room_number}-B{i + 1}",  # ✅ CORRECT
                # Example: "101-B1", "101-B2", etc.
                status=BedStatus.AVAILABLE,
            )
            self.session.add(bed)

        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def update_room(self, room_id: str, payload: RoomUpdateRequest) -> Room:
        """Update room details."""
        room = await self.repository.get_room_by_id(room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found.")
        update_data = payload.dict(exclude_unset=True)
        if "room_type" in update_data and update_data["room_type"]:
            update_data["room_type"] = update_data["room_type"].upper().replace("-", "_")
        
        for field, value in update_data.items():
            setattr(room, field, value)
        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def list_beds(self, room_id: str) -> list[Bed]:
        """List all beds in a room."""
        return await self.repository.list_beds(room_id)

    async def create_bed(self, room_id: str, payload: BedCreateRequest) -> Bed:
        """Add a bed to a room."""
        room = await self.repository.get_room_by_id(room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found.")
        
        # Check if bed number already exists in this room
        existing_beds = await self.repository.list_beds(room_id)
        existing_bed_numbers = [bed.bed_number for bed in existing_beds]
        
        if payload.bed_number in existing_bed_numbers:
            raise HTTPException(
                status_code=409,
                detail=f"Bed number '{payload.bed_number}' already exists in this room."
            )
        
        # Instead of erroring at capacity, just increase total_beds
        if len(existing_beds) >= room.total_beds:
            # Auto-increase capacity
            room.total_beds += 1
            print(f"⚠️ Auto-increased room {room.room_number} capacity to {room.total_beds}")
        
        bed = Bed(
            hostel_id=room.hostel_id,
            room_id=room_id,
            bed_number=payload.bed_number,
            status=payload.status or BedStatus.AVAILABLE,
        )
        self.session.add(bed)
        await self.session.commit()
        await self.session.refresh(bed)
        return bed


    async def update_bed(self, bed_id: str, payload: BedUpdateRequest) -> Bed:
        """Update bed details including moving to different room."""
        bed = await self.repository.get_bed_by_id(bed_id)
        if bed is None:
            raise HTTPException(status_code=404, detail="Bed not found.")
        
        # Handle moving bed to different room
        if payload.room_id is not None and payload.room_id != str(bed.room_id):
            # Verify new room exists
            new_room = await self.repository.get_room_by_id(payload.room_id)
            if new_room is None:
                raise HTTPException(status_code=404, detail="Target room not found.")
            
            # Verify same hostel
            if str(new_room.hostel_id) != str(bed.hostel_id):
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot move bed to a room in a different hostel."
                )
            
            # Check if bed has active bookings
            from app.models.booking import Booking, BookingStatus
            active_booking = await self.session.execute(
                select(Booking).where(
                    Booking.bed_id == bed_id,
                    Booking.status.in_([
                        BookingStatus.APPROVED,
                        BookingStatus.CHECKED_IN,
                        BookingStatus.PENDING_APPROVAL
                    ])
                )
            )
            if active_booking.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail="Cannot move bed with active bookings. Please check-out students first."
                )
            
            # Check if bed number already exists in target room
            existing_beds = await self.repository.list_beds(payload.room_id)
            if bed.bed_number in [b.bed_number for b in existing_beds]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Bed number '{bed.bed_number}' already exists in target room."
                )
            
            # Move the bed
            bed.room_id = payload.room_id
        
        # Handle bed number change
        if payload.bed_number and payload.bed_number != bed.bed_number:
            # Check for duplicate in current room
            target_room_id = payload.room_id if payload.room_id else bed.room_id
            existing_beds = await self.repository.list_beds(target_room_id)
            if payload.bed_number in [b.bed_number for b in existing_beds if b.id != bed_id]:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Bed number '{payload.bed_number}' already exists in this room."
                )
            bed.bed_number = payload.bed_number
        
        # Handle status change - VALIDATE HERE
        if payload.status is not None:
            # Import BedStatus if not already imported
            from app.models.room import BedStatus
            
            # Convert to lowercase for case-insensitive comparison
            status_value = payload.status.lower().strip()
            
            # Map status values
            valid_statuses = {
                "available": BedStatus.AVAILABLE,
                "occupied": BedStatus.OCCUPIED,
                "maintenance": BedStatus.MAINTENANCE,
                "reserved": BedStatus.RESERVED
            }
            
            if status_value in valid_statuses:
                bed.status = valid_statuses[status_value]
            else:
                # Return 400 for invalid status
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: available, occupied, maintenance, reserved. Got: '{payload.status}'"
                )
        
        await self.session.commit()
        await self.session.refresh(bed)
        return bed


    async def delete_student(self, student_id: str) -> None:
        """
        Hard delete a student. 
        Unlinks payments and bookings to avoid foreign key constraints.
        """
        result = await self.session.execute(select(Student).where(Student.id == student_id))
        student = result.scalar_one_or_none()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")
            
        # Unlink payments
        await self.session.execute(
            update(Payment).where(Payment.student_id == student_id).values(student_id=None)
        )
        
        # Free up the bed
        if student.bed_id:
            await self.session.execute(
                update(Bed).where(Bed.id == student.bed_id).values(status="available")
            )
            
        await self.session.delete(student)
        await self.session.commit()

    async def list_students(self, hostel_id: str) -> list[dict]:
        """List all checked-in students for a hostel."""
        students_data = await self.repository.list_students(hostel_id)
        # The repository now returns dict objects directly
        return students_data

    async def list_students_for_hostels(self, hostel_ids: list[str]) -> list[dict]:
        """List students across multiple hostels."""
        students_data = await self.repository.list_students_by_hostel_ids(hostel_ids)
        return students_data

    async def list_attendance(self, hostel_id: str):
        """List attendance records for a hostel."""
        return await self.repository.list_attendance(hostel_id)

    async def get_dashboard(self, hostel_ids: list[str]) -> dict:
        """Admin dashboard metrics."""
        if not hostel_ids:
            return {"hostels": 0, "rooms": 0, "students": 0,
                    "complaints": 0, "maintenance_items": 0, "payments": 0}
        rooms = await self.session.execute(
            select(func.count()).select_from(Room).where(Room.hostel_id.in_(hostel_ids))
        )
        students = await self.session.execute(
            select(func.count()).select_from(Student).where(Student.hostel_id.in_(hostel_ids))
        )
        complaints = await self.session.execute(
            select(func.count()).select_from(Complaint).where(
                Complaint.hostel_id.in_(hostel_ids),
                Complaint.status.in_(["open", "in_progress"])
            )
        )
        maintenance = await self.session.execute(
            select(func.count()).select_from(MaintenanceRequest).where(
                MaintenanceRequest.hostel_id.in_(hostel_ids),
                MaintenanceRequest.status.in_(["open", "in_progress", "pending"])
            )
        )
        payments = await self.session.execute(
            select(func.count()).select_from(Payment).where(Payment.hostel_id.in_(hostel_ids))
        )
        return {
            "hostels": len(hostel_ids),
            "rooms": int(rooms.scalar_one() or 0),
            "students": int(students.scalar_one() or 0),
            "complaints": int(complaints.scalar_one() or 0),
            "maintenance_items": int(maintenance.scalar_one() or 0),
            "payments": int(payments.scalar_one() or 0),
        }

    async def list_supervisors(self, hostel_id: str):
        """List supervisors assigned to a hostel."""
        return await self.repository.list_supervisors(hostel_id)

    async def create_supervisor(self, hostel_id: str, assigned_by: str, payload: SupervisorCreateRequest) -> User:
        """Create a supervisor and assign to hostel."""
        # Check if email already exists
        existing_email = await self.session.execute(
            select(User).where(User.email == payload.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{payload.email}' is already registered."
            )

        # Check if phone already exists
        existing_phone = await self.session.execute(
            select(User).where(User.phone == payload.phone)
        )
        if existing_phone.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phone number '{payload.phone}' is already registered."
            )

        # Rule: Each hostel can have only one supervisor.
        from app.models.hostel import SupervisorHostelMapping
        existing_hostel_mapping = await self.session.execute(
            select(SupervisorHostelMapping).where(SupervisorHostelMapping.hostel_id == hostel_id)
        )
        if existing_hostel_mapping.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This hostel already has a supervisor assigned."
            )

        user = User(
            email=payload.email,
            phone=payload.phone,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=UserRole.SUPERVISOR,
            is_active=True,
            is_email_verified=True,
            is_phone_verified=True,
        )
        self.session.add(user)
        await self.session.flush()
        await self.repository.assign_supervisor_to_hostel(
            supervisor_id=str(user.id),
            hostel_id=hostel_id,
            assigned_by=assigned_by,
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user


    async def add_student_direct(self, hostel_id: str, actor_id: str, payload):
        bed_result = await self.session.execute(select(Bed).where(Bed.id == payload.bed_id))
        bed = bed_result.scalar_one_or_none()
        if bed is None:
            raise HTTPException(status_code=404, detail="Bed not found.")
        if str(bed.hostel_id) != hostel_id:
            raise HTTPException(status_code=400, detail="Bed does not belong to this hostel.")

        # Validate gender if provided
        if hasattr(payload, 'gender') and payload.gender:
            valid_genders = ["M", "F", "Other", "MALE", "FEMALE", "male", "female", "other"]
            if payload.gender not in valid_genders:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid gender. Must be one of: M, F, Other. Got: '{payload.gender}'"
                )
            # Normalize gender
            gender_value = payload.gender.upper()
            if gender_value == "MALE":
                gender_value = "M"
            elif gender_value == "FEMALE":
                gender_value = "F"
            elif gender_value == "OTHER":
                gender_value = "Other"
            else:
                gender_value = gender_value  # Keep as is (M, F, Other)
        else:
            gender_value = None

        user = User(
            email=payload.email,
            phone=payload.phone,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=UserRole.STUDENT,
            is_active=True,
            is_email_verified=True,
            is_phone_verified=True,
        )
        try:
            self.session.add(user)
            await self.session.flush()
        except Exception as e:
            await self.session.rollback()
            err_str = str(e).lower()
            if "ix_users_email" in err_str:
                raise HTTPException(status_code=409, detail="A user with this email already exists.")
            if "ix_users_phone" in err_str:
                raise HTTPException(status_code=409, detail="A user with this phone number already exists.")
            raise

        check_in = date.fromisoformat(payload.check_in_date)
        check_out = date.fromisoformat(payload.check_out_date)
        booking_number = f"SE-{str(user.id)[:8].upper()}"

        # Parse date_of_birth if provided
        date_of_birth = None
        if hasattr(payload, 'date_of_birth') and payload.date_of_birth:
            try:
                date_of_birth = date.fromisoformat(payload.date_of_birth)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_of_birth format. Use YYYY-MM-DD.")

        booking = Booking(
            visitor_id=str(user.id),
            hostel_id=hostel_id,
            room_id=payload.room_id,
            bed_id=payload.bed_id,
            booking_number=booking_number,
            booking_mode=BookingMode(payload.booking_mode),
            check_in_date=check_in,
            check_out_date=check_out,
            base_rent_amount=0,
            security_deposit=0,
            booking_advance=0,
            grand_total=0,
            status=BookingStatus.CHECKED_IN,
            full_name=payload.full_name,
            approved_by=actor_id,
            gender=gender_value,  # ← ADD THIS
            date_of_birth=date_of_birth,  # ← ADD THIS
        )
        self.session.add(booking)
        await self.session.flush()

        bed_stay = BedStay(
            hostel_id=hostel_id,
            bed_id=payload.bed_id,
            booking_id=str(booking.id),
            start_date=check_in,
            end_date=check_out,
            status=BedStayStatus.ACTIVE,
        )
        self.session.add(bed_stay)

        bed.status = BedStatus.OCCUPIED

        student_number = f"STU-{str(booking.id)[:8].upper()}"
        student = Student(
            user_id=str(user.id),
            hostel_id=hostel_id,
            room_id=payload.room_id,
            bed_id=payload.bed_id,
            booking_id=str(booking.id),
            student_number=student_number,
            check_in_date=check_in,
            check_out_date=check_out,
            status=StudentStatus.ACTIVE,
        )
        self.session.add(student)

        await self.session.commit()
        await self.session.refresh(student)

        return {
            "student_id": str(student.id),
            "student_number": student.student_number,
            "user_id": str(user.id),
            "booking_id": str(booking.id),
            "booking_number": booking.booking_number,
            "full_name": user.full_name,
            "email": user.email,
            "room_id": str(student.room_id),
            "bed_id": str(student.bed_id),
            "check_in_date": str(student.check_in_date),
            "gender": gender_value,  # ← ADD THIS
            "date_of_birth": str(date_of_birth) if date_of_birth else None,  # ← ADD THIS
        }

    async def delete_room(self, room_id: str) -> None:
        """Delete a room and all its associated data"""
        room = await self.repository.get_room_by_id(room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found.")
        
        # First, get all beds in this room
        beds = await self.repository.list_beds(room_id)
        
        # Check if any beds are referenced in active bookings
        from app.models.booking import Booking, BookingStatus
        
        for bed in beds:
            # Check for active bookings using this bed
            result = await self.session.execute(
                select(Booking).where(
                    Booking.bed_id == bed.id,
                    Booking.status.in_([
                        BookingStatus.APPROVED,
                        BookingStatus.CHECKED_IN,
                        BookingStatus.PENDING_APPROVAL
                    ])
                )
            )
            active_bookings = result.scalars().all()
            
            if active_bookings:
                # Option 1: Raise error with details
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete room: Bed {bed.bed_number} has {len(active_bookings)} active booking(s). "
                        f"Please cancel or complete these bookings first."
                )
        
        # If no active bookings, proceed with deletion
        # First, delete or update bookings that reference these beds
        for bed in beds:
            # Update any draft/payment_pending bookings to remove bed reference
            await self.session.execute(
                update(Booking)
                .where(
                    Booking.bed_id == bed.id,
                    Booking.status.in_([
                        BookingStatus.DRAFT,
                        BookingStatus.PAYMENT_PENDING
                    ])
                )
                .values(bed_id=None)
            )
            
            # Delete any completed/cancelled bookings that reference this bed
            await self.session.execute(
                delete(Booking)
                .where(
                    Booking.bed_id == bed.id,
                    Booking.status.in_([
                        BookingStatus.CANCELLED,
                        BookingStatus.COMPLETED,
                        BookingStatus.REJECTED
                    ])
                )
            )
        
        # Now delete beds (cascade should handle, but explicit order is safer)
        for bed in beds:
            await self.session.delete(bed)
        
        # Finally delete the room
        await self.repository.delete_room(room)
        await self.session.commit()
        
    async def get_complete_student_by_id(self, student_id: str) -> dict | None:
        """Get complete student details with all related information"""
        
        # Query student with all joins
        result = await self.session.execute(
            select(
                Student,
                User.full_name,
                User.email,
                User.phone,
                User.profile_picture_url,
                Room.room_number,
                Room.room_type,
                Room.floor,
                Room.monthly_rent,
                Room.daily_rent,
                Bed.bed_number,
                Booking.booking_number,
                Booking.booking_mode,
                Booking.gender,
                Booking.date_of_birth,
                Booking.occupation,
                Booking.institution,
                Booking.emergency_contact_name,
                Booking.emergency_contact_phone,
                Booking.booking_advance,
                Hostel.name.label("hostel_name"),
                Hostel.city.label("hostel_city"),
                Hostel.hostel_type.label("hostel_type"),
            )
            .select_from(Student)
            .join(User, User.id == Student.user_id)
            .outerjoin(Room, Room.id == Student.room_id)
            .outerjoin(Bed, Bed.id == Student.bed_id)
            .outerjoin(Booking, Booking.id == Student.booking_id)
            .outerjoin(Hostel, Hostel.id == Student.hostel_id)
            .where(Student.id == student_id)
        )
        
        row = result.first()
        if not row:
            return None
        
        student = row[0]
        
        # Get payment summary
        payment_summary = await self._get_student_payment_summary(str(student.id))
        
        # Helper to convert Decimal to float
        def to_float(val):
            if val is None:
                return None
            return float(val) if hasattr(val, '__float__') else val
        
        return {
            # Student identifiers
            "id": str(student.id),
            "student_number": student.student_number,
            "user_id": str(student.user_id),
            
            # Personal Information
            "full_name": row.full_name,
            "email": row.email,
            "phone": row.phone,
            "gender": row.gender,
            "date_of_birth": row.date_of_birth,
            "profile_picture_url": row.profile_picture_url,
            
            # Student Information
            "status": student.status.value if hasattr(student.status, 'value') else str(student.status),
            "check_in_date": student.check_in_date,
            "check_out_date": student.check_out_date,
            
            # Room Information
            "room_id": str(student.room_id),
            "room_number": row.room_number,
            "room_type": row.room_type.value if row.room_type and hasattr(row.room_type, 'value') else row.room_type,
            "floor": row.floor,
            "monthly_rent": to_float(row.monthly_rent),
            "daily_rent": to_float(row.daily_rent),
            
            # Bed Information
            "bed_id": str(student.bed_id),
            "bed_number": row.bed_number,
            
            # Booking Information
            "booking_id": str(student.booking_id),
            "booking_number": row.booking_number,
            "booking_mode": row.booking_mode.value if row.booking_mode and hasattr(row.booking_mode, 'value') else row.booking_mode,
            "booking_advance": to_float(row.booking_advance),
            
            # Hostel Information
            "hostel_id": str(student.hostel_id),
            "hostel_name": row.hostel_name,
            "hostel_city": row.hostel_city,
            "hostel_type": row.hostel_type.value if row.hostel_type and hasattr(row.hostel_type, 'value') else row.hostel_type,
            
            # Payment Information
            "payment_status": payment_summary.get("payment_status", "unknown"),
            "total_paid": payment_summary.get("total_paid", 0),
            "last_payment_date": payment_summary.get("last_payment_date"),
            "last_payment_amount": payment_summary.get("last_payment_amount", 0),
            "next_payment_due": payment_summary.get("next_payment_due"),
            "advance_paid": payment_summary.get("advance_paid", 0),
            
            # Additional Information
            "occupation": row.occupation,
            "institution": row.institution,
            "emergency_contact_name": row.emergency_contact_name,
            "emergency_contact_phone": row.emergency_contact_phone,
            
            # Timestamps
            "created_at": student.created_at,
            "updated_at": student.updated_at,
        }


    async def _get_student_payment_summary(self, student_id: str) -> dict:
        """Get payment summary for a student"""
        from decimal import Decimal
        
        # Get all payments for this student
        result = await self.session.execute(
            select(Payment)
            .where(Payment.student_id == student_id)
            .order_by(Payment.created_at.desc())
        )
        payments = result.scalars().all()
        
        total_paid = Decimal('0.0')
        last_payment = None
        last_amount = Decimal('0.0')
        
        for payment in payments:
            if payment.status == "captured":
                total_paid += Decimal(str(payment.amount))
                if not last_payment or (payment.paid_at and payment.paid_at > last_payment):
                    last_payment = payment.paid_at
                    last_amount = Decimal(str(payment.amount))
        
        # Get student's monthly rent from room
        student = await self.repository.get_student_by_id(student_id)
        monthly_rent = Decimal('0.0')
        if student and student.room_id:
            room_result = await self.session.execute(
                select(Room.monthly_rent).where(Room.id == student.room_id)
            )
            monthly_rent_val = room_result.scalar_one_or_none()
            if monthly_rent_val:
                monthly_rent = Decimal(str(monthly_rent_val))
        
        # Calculate pending amount (convert both to Decimal)
        pending = max(Decimal('0.0'), monthly_rent - total_paid)
        
        # Determine payment status
        if total_paid >= monthly_rent and monthly_rent > 0:
            payment_status = "paid"
        elif total_paid > 0:
            payment_status = "partial"
        else:
            payment_status = "unpaid"
        
        # Calculate next due date (typically 1 month after check-in)
        next_due = None
        if student and student.check_in_date:
            next_due = student.check_in_date.replace(day=1)
            # Add 1 month
            if next_due.month == 12:
                next_due = next_due.replace(year=next_due.year + 1, month=1)
            else:
                next_due = next_due.replace(month=next_due.month + 1)
        
        # Get advance from booking
        advance_paid = Decimal('0.0')
        if student and student.booking_id:
            booking_result = await self.session.execute(
                select(Booking.booking_advance).where(Booking.id == student.booking_id)
            )
            advance_val = booking_result.scalar_one_or_none()
            if advance_val:
                advance_paid = Decimal(str(advance_val))
        
        return {
            "payment_status": payment_status,
            "total_paid": float(total_paid),
            "last_payment_date": last_payment,
            "last_payment_amount": float(last_amount),
            "next_payment_due": next_due,
            "advance_paid": float(advance_paid),
        }


    async def get_student_with_hostel_id(self, student_id: str) -> dict | None:
        """Get just the hostel_id for a student (for permission checks)"""
        result = await self.session.execute(
            select(Student.hostel_id).where(Student.id == student_id)
        )
        hostel_id = result.scalar_one_or_none()
        if hostel_id:
            return {"hostel_id": str(hostel_id)}
        return None
        
    async def get_supervisor_by_id(self, supervisor_id: str) -> User | None:
        """Get supervisor by ID"""
        return await self.repository.get_supervisor_by_id(supervisor_id)

    async def update_supervisor(
        self, 
        supervisor_id: str, 
        payload,  # SupervisorUpdateRequest
        admin_hostel_ids: set[str]
    ) -> User:
        """Update supervisor details"""
        supervisor = await self.repository.get_supervisor_by_id(supervisor_id)
        if supervisor is None:
            raise HTTPException(status_code=404, detail="Supervisor not found.")
        
        # Check if supervisor belongs to any of admin's hostels
        from app.models.hostel import SupervisorHostelMapping
        result = await self.session.execute(
            select(SupervisorHostelMapping.hostel_id).where(
                SupervisorHostelMapping.supervisor_id == supervisor_id
            )
        )
        supervisor_hostel_ids = {str(hid) for hid in result.scalars().all()}
        
        if not supervisor_hostel_ids.intersection(admin_hostel_ids):
            raise HTTPException(
                status_code=403, 
                detail="You don't have permission to update this supervisor."
            )
        
        # Check if email is being changed and if it's already taken
        if payload.email and payload.email != supervisor.email:
            existing = await self.session.execute(
                select(User).where(User.email == payload.email)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, 
                    detail="Email already registered by another user."
                )
        
        # Check if phone is being changed and if it's already taken
        if payload.phone and payload.phone != supervisor.phone:
            existing = await self.session.execute(
                select(User).where(User.phone == payload.phone)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, 
                    detail="Phone number already registered by another user."
                )
        
        # Prepare update data
        update_data = payload.dict(exclude_unset=True)
        
        # Update supervisor
        supervisor = await self.repository.update_supervisor(supervisor, update_data)
        await self.session.commit()
        await self.session.refresh(supervisor)
        
        return supervisor

    async def delete_supervisor(
        self, 
        supervisor_id: str, 
        admin_hostel_ids: set[str]
    ) -> None:
        """Delete supervisor"""
        supervisor = await self.repository.get_supervisor_by_id(supervisor_id)
        if supervisor is None:
            raise HTTPException(status_code=404, detail="Supervisor not found.")
        
        # Check if supervisor belongs to any of admin's hostels
        from app.models.hostel import SupervisorHostelMapping
        result = await self.session.execute(
            select(SupervisorHostelMapping.hostel_id).where(
                SupervisorHostelMapping.supervisor_id == supervisor_id
            )
        )
        supervisor_hostel_ids = {str(hid) for hid in result.scalars().all()}
        
        if not supervisor_hostel_ids.intersection(admin_hostel_ids):
            raise HTTPException(
                status_code=403, 
                detail="You don't have permission to delete this supervisor."
            )
        
        # Delete hostel mappings first
        await self.repository.delete_supervisor_mappings(supervisor_id)
        
        # Delete the supervisor user
        await self.repository.delete_supervisor(supervisor)
        await self.session.commit()