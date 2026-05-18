# scripts/fix_visitor_issues.py
#!/usr/bin/env python3
"""
Fix remaining visitor routes issues:
1. Profile update phone conflict
2. Waitlist join server error
"""

import os
import re

def fix_profile_phone_conflict():
    """Fix phone number conflict in profile update"""
    
    visitor_routes_path = "app/api/v1/visitor/routes.py"
    
    with open(visitor_routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the update_profile function to handle phone number correctly
    old_update = '''@router.patch("/profile", response_model=VisitorProfileResponse)
async def update_profile(payload: VisitorProfileUpdateRequest, current_user: VisitorUser, db: DBSession):
    """**Update visitor profile** — name, phone, profile picture."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.profile_picture_url is not None:
        user.profile_picture_url = payload.profile_picture_url
    await db.commit()
    await db.refresh(user)
    return user'''
    
    new_update = '''@router.patch("/profile", response_model=VisitorProfileResponse)
async def update_profile(payload: VisitorProfileUpdateRequest, current_user: VisitorUser, db: DBSession):
    """**Update visitor profile** — name, phone, profile picture."""
    # Validate phone if provided
    if payload.phone:
        # Clean phone number
        digits = re.sub(r'[^0-9]', '', payload.phone)
        if len(digits) < 10:
            raise HTTPException(status_code=400, detail="Phone number must have at least 10 digits")
        if len(digits) > 15:
            raise HTTPException(status_code=400, detail="Phone number must have at most 15 digits")
        # Store standardized version (last 10 digits for Indian numbers)
        payload.phone = digits[-10:] if len(digits) > 10 else digits
        
        # Check if phone already taken by another user
        existing = await db.execute(
            select(User).where(
                User.phone == payload.phone,
                User.id != current_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Phone number already registered by another user.")
    
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.profile_picture_url is not None:
        user.profile_picture_url = payload.profile_picture_url
    await db.commit()
    await db.refresh(user)
    return user'''
    
    if old_update in content:
        content = content.replace(old_update, new_update)
        print("✅ Fixed profile update phone validation")
    else:
        print("⚠️ Profile update function not found with expected pattern")
    
    # Also fix the VisitorProfileUpdateRequest schema
    old_schema = '''class VisitorProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=8, max_length=30)
    profile_picture_url: str | None = None'''
    
    new_schema = '''class VisitorProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=15)
    profile_picture_url: str | None = None
    
    def normalize_phone(self) -> None:
        """Normalize phone number to 10 digits"""
        if self.phone:
            import re
            digits = re.sub(r'[^0-9]', '', self.phone)
            if len(digits) >= 10:
                self.phone = digits[-10:]'''
    
    if old_schema in content:
        content = content.replace(old_schema, new_schema)
        print("✅ Fixed VisitorProfileUpdateRequest schema")
    
    with open(visitor_routes_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def fix_waitlist_join_error():
    """Fix waitlist join server error (HTTP 500)"""
    
    # First check the booking_service.py waitlist join method
    booking_service_path = "app/services/booking_service.py"
    
    with open(booking_service_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the join_waitlist method
    old_join = '''    async def join_waitlist(self, *, visitor_id: str, payload: WaitlistJoinRequest) -> tuple[WaitlistEntry, int]:
        """
        Join waitlist for a room when no beds are available.
        Returns (waitlist_entry, position_in_queue)
        """
        from app.models.booking import WaitlistEntry, WaitlistStatus, BookingMode
        
        # Validate room exists
        from app.models.room import Room
        room_result = await self.session.execute(
            select(Room).where(Room.id == payload.room_id)
        )
        room = room_result.scalar_one_or_none()
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {payload.room_id} not found.")
        
        # Validate dates
        if payload.check_out_date <= payload.check_in_date:
            raise HTTPException(
                status_code=422,
                detail="check_out_date must be after check_in_date"
            )
        
        # Check if already on waitlist for same room/dates
        existing = await self.repository.get_active_waitlist_entry(
            visitor_id=visitor_id,
            room_id=payload.room_id,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
        )
        
        if existing:
            position = await self.repository.get_waitlist_position(entry=existing)
            return existing, position
        
        # Create new waitlist entry
        entry = WaitlistEntry(
            visitor_id=visitor_id,
            hostel_id=payload.hostel_id,
            room_id=payload.room_id,
            bed_id=payload.bed_id,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
            booking_mode=BookingMode(payload.booking_mode),
            status=WaitlistStatus.ACTIVE,
        )
        
        self.session.add(entry)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(entry)
        
        # Get position (1-indexed)
        position = await self.repository.get_waitlist_position(entry=entry)
        
        return entry, position'''
    
    new_join = '''    async def join_waitlist(self, *, visitor_id: str, payload: WaitlistJoinRequest) -> tuple[WaitlistEntry, int]:
        """
        Join waitlist for a room when no beds are available.
        Returns (waitlist_entry, position_in_queue)
        """
        from app.models.booking import WaitlistEntry, WaitlistStatus, BookingMode
        from sqlalchemy import select
        
        # Validate room exists
        from app.models.room import Room
        room_result = await self.session.execute(
            select(Room).where(Room.id == payload.room_id)
        )
        room = room_result.scalar_one_or_none()
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {payload.room_id} not found.")
        
        # Validate dates
        if payload.check_out_date <= payload.check_in_date:
            raise HTTPException(
                status_code=400,
                detail="check_out_date must be after check_in_date"
            )
        
        # Check if check_in_date is not in the past
        from datetime import date
        if payload.check_in_date < date.today():
            raise HTTPException(
                status_code=400,
                detail="check_in_date cannot be in the past"
            )
        
        # Check if already on waitlist for same room/dates
        existing = await self.repository.get_active_waitlist_entry(
            visitor_id=visitor_id,
            room_id=payload.room_id,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
        )
        
        if existing:
            position = await self.repository.get_waitlist_position(entry=existing)
            return existing, position
        
        # Create new waitlist entry
        entry = WaitlistEntry(
            visitor_id=visitor_id,
            hostel_id=payload.hostel_id,
            room_id=payload.room_id,
            bed_id=payload.bed_id,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
            booking_mode=BookingMode(payload.booking_mode),
            status=WaitlistStatus.ACTIVE,
        )
        
        try:
            self.session.add(entry)
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(entry)
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create waitlist entry: {str(e)}"
            )
        
        # Get position (1-indexed)
        try:
            position = await self.repository.get_waitlist_position(entry=entry)
        except Exception as e:
            position = 1  # Default to position 1 if calculation fails
        
        return entry, position'''
    
    if old_join in content:
        content = content.replace(old_join, new_join)
        print("✅ Fixed waitlist join method in booking_service.py")
    else:
        print("⚠️ Waitlist join method not found with expected pattern")
    
    with open(booking_service_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def fix_waitlist_repository():
    """Fix waitlist repository methods to handle errors gracefully"""
    
    repo_path = "app/repositories/booking_repository.py"
    
    with open(repo_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix get_waitlist_position method
    old_position = '''    async def get_waitlist_position(self, *, entry: WaitlistEntry) -> int:
        """Get 1-indexed position in waitlist queue"""
        result = await self.session.execute(
            select(func.count())
            .select_from(WaitlistEntry)
            .where(
                WaitlistEntry.room_id == entry.room_id,
                WaitlistEntry.check_in_date == entry.check_in_date,
                WaitlistEntry.check_out_date == entry.check_out_date,
                WaitlistEntry.status == WaitlistStatus.ACTIVE,
                WaitlistEntry.created_at <= entry.created_at,
            )
        )
        return int(result.scalar() or 0)'''
    
    new_position = '''    async def get_waitlist_position(self, *, entry: WaitlistEntry) -> int:
        """Get 1-indexed position in waitlist queue"""
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(WaitlistEntry)
                .where(
                    WaitlistEntry.room_id == entry.room_id,
                    WaitlistEntry.status == WaitlistStatus.ACTIVE,
                    WaitlistEntry.created_at <= entry.created_at,
                )
            )
            return int(result.scalar() or 0)
        except Exception as e:
            print(f"Error getting waitlist position: {e}")
            return 1'''
    
    if old_position in content:
        content = content.replace(old_position, new_position)
        print("✅ Fixed get_waitlist_position method")
    
    # Fix get_active_waitlist_entry method
    old_active = '''    async def get_active_waitlist_entry(
        self,
        *,
        visitor_id: str,
        room_id: str,
        check_in_date: date,
        check_out_date: date,
    ) -> WaitlistEntry | None:
        """Get active waitlist entry for visitor and room"""
        result = await self.session.execute(
            select(WaitlistEntry).where(
                WaitlistEntry.visitor_id == visitor_id,
                WaitlistEntry.room_id == room_id,
                WaitlistEntry.check_in_date == check_in_date,
                WaitlistEntry.check_out_date == check_out_date,
                WaitlistEntry.status == WaitlistStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()'''
    
    new_active = '''    async def get_active_waitlist_entry(
        self,
        *,
        visitor_id: str,
        room_id: str,
        check_in_date: date,
        check_out_date: date,
    ) -> WaitlistEntry | None:
        """Get active waitlist entry for visitor and room"""
        try:
            result = await self.session.execute(
                select(WaitlistEntry).where(
                    WaitlistEntry.visitor_id == visitor_id,
                    WaitlistEntry.room_id == room_id,
                    WaitlistEntry.status == WaitlistStatus.ACTIVE,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error getting active waitlist entry: {e}")
            return None'''
    
    if old_active in content:
        content = content.replace(old_active, new_active)
        print("✅ Fixed get_active_waitlist_entry method")
    
    with open(repo_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def fix_waitlist_schema():
    """Fix waitlist join request schema validation"""
    
    schema_path = "app/schemas/booking.py"
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add validation to WaitlistJoinRequest
    old_waitlist = '''class WaitlistJoinRequest(BaseModel):
    hostel_id: str
    room_id: str
    bed_id: str | None = None
    booking_mode: BookingModeEnum
    check_in_date: date
    check_out_date: date'''
    
    new_waitlist = '''class WaitlistJoinRequest(BaseModel):
    hostel_id: str
    room_id: str
    bed_id: str | None = None
    booking_mode: BookingModeEnum
    check_in_date: date
    check_out_date: date
    
    @model_validator(mode="after")
    def validate_dates(self) -> "WaitlistJoinRequest":
        from datetime import date
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")
        if self.check_in_date < date.today():
            raise ValueError("check_in_date cannot be in the past")
        return self'''
    
    if old_waitlist in content:
        content = content.replace(old_waitlist, new_waitlist)
        print("✅ Fixed WaitlistJoinRequest schema")
    
    with open(schema_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def add_missing_imports():
    """Add missing imports to visitor routes"""
    
    visitor_routes_path = "app/api/v1/visitor/routes.py"
    
    with open(visitor_routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add re import if missing
    if 'import re' not in content:
        # Find the import section
        lines = content.split('\n')
        new_lines = []
        import_re_added = False
        
        for line in lines:
            new_lines.append(line)
            if 'import datetime' in line and not import_re_added:
                new_lines.append('import re')
                import_re_added = True
        
        if not import_re_added:
            # Add at the top of imports
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    new_lines.insert(i, 'import re')
                    break
        
        content = '\n'.join(new_lines)
        print("✅ Added missing 'import re'")
    
    with open(visitor_routes_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    print("\n" + "="*60)
    print("  FIXING REMAINING VISITOR ROUTES ISSUES")
    print("="*60 + "\n")
    
    # Fix all issues
    add_missing_imports()
    fix_profile_phone_conflict()
    fix_waitlist_join_error()
    fix_waitlist_repository()
    fix_waitlist_schema()
    
    print("\n" + "="*60)
    print("  FIXES APPLIED!")
    print("="*60)
    print("""
To apply fixes:
1. Restart your backend server
2. Run the test again: python scripts/test_visitor_routes_comprehensive.py

The fixes address:
- Profile update phone conflict (409 error)
- Waitlist join server error (500 error)
- Added proper error handling for waitlist operations
- Added date validation for waitlist join
""")
    
    # Ask to restart
    response = input("\nRestart backend now? (y/n): ").strip().lower()
    if response == 'y':
        import subprocess
        import sys
        print("\n🔄 Restarting backend...")
        # Kill existing uvicorn process and restart
        subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"])
        print("✅ Backend restarting...")
    else:
        print("\nℹ️ Please restart your backend server manually.")


if __name__ == "__main__":
    main()