# scripts/fix_profile_update.py
#!/usr/bin/env python3
"""
Fix profile update HTTP 409 conflict issue
"""

import re

def fix_profile_update():
    """Fix the profile update endpoint to handle phone number conflicts properly"""
    
    visitor_routes_path = "app/api/v1/visitor/routes.py"
    
    with open(visitor_routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the update_profile function
    old_function = '''@router.patch("/profile", response_model=VisitorProfileResponse)
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
    
    new_function = '''@router.patch("/profile", response_model=VisitorProfileResponse)
async def update_profile(payload: VisitorProfileUpdateRequest, current_user: VisitorUser, db: DBSession):
    """**Update visitor profile** — name, phone, profile picture."""
    import re
    
    # Normalize phone if provided
    if payload.phone is not None:
        # Remove all non-digit characters
        digits = re.sub(r'[^0-9]', '', payload.phone)
        
        # Validate phone length
        if len(digits) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Phone number must have at least 10 digits"
            )
        if len(digits) > 15:
            raise HTTPException(
                status_code=400, 
                detail="Phone number must have at most 15 digits"
            )
        
        # Standardize to 10 digits (last 10 digits for Indian numbers)
        if len(digits) > 10:
            digits = digits[-10:]
        
        # Check if phone is different from current and already taken
        if digits != current_user.phone:
            existing = await db.execute(
                select(User).where(
                    User.phone == digits,
                    User.id != current_user.id
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, 
                    detail=f"Phone number {digits} is already registered by another user."
                )
        payload.phone = digits
    
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Update fields
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.profile_picture_url is not None:
        user.profile_picture_url = payload.profile_picture_url
    
    await db.commit()
    await db.refresh(user)
    return user'''
    
    if old_function in content:
        content = content.replace(old_function, new_function)
        print("✅ Fixed update_profile function")
    else:
        # Try to find the function with different formatting
        print("⚠️ Old function pattern not found, trying alternative...")
        
        # Alternative pattern
        alt_pattern = r'(@router\.patch\("/profile".*?async def update_profile.*?return user)'
        if re.search(alt_pattern, content, re.DOTALL):
            content = re.sub(alt_pattern, new_function, content, flags=re.DOTALL)
            print("✅ Fixed update_profile function (alternative pattern)")
        else:
            print("❌ Could not find update_profile function")
            return False
    
    with open(visitor_routes_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def fix_profile_schema():
    """Fix the profile update request schema"""
    
    schema_path = "app/schemas/__init__.py"
    visitor_schema_path = "app/api/v1/visitor/routes.py"
    
    # Find and fix the VisitorProfileUpdateRequest class in routes.py
    with open(visitor_schema_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_schema = '''class VisitorProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=8, max_length=30)
    profile_picture_url: str | None = None'''
    
    new_schema = '''class VisitorProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=15)
    profile_picture_url: str | None = None
    
    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: str | None) -> str | None:
        """Normalize phone number to 10 digits"""
        if v is None:
            return v
        import re
        # Remove all non-digits
        digits = re.sub(r'[^0-9]', '', str(v))
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        if len(digits) > 15:
            raise ValueError("Phone number must have at most 15 digits")
        # Return last 10 digits for Indian numbers
        return digits[-10:] if len(digits) > 10 else digits'''
    
    if old_schema in content:
        content = content.replace(old_schema, new_schema)
        print("✅ Fixed VisitorProfileUpdateRequest schema")
    else:
        print("⚠️ Could not find VisitorProfileUpdateRequest schema")
    
    with open(visitor_schema_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def add_phone_normalization_helper():
    """Add a helper function for phone normalization"""
    
    visitor_routes_path = "app/api/v1/visitor/routes.py"
    
    with open(visitor_routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add normalize_phone helper function at the top of the file
    helper_function = '''
def normalize_phone(phone: str) -> str:
    """Normalize phone number to standard format"""
    import re
    if not phone:
        return phone
    # Remove all non-digits
    digits = re.sub(r'[^0-9]', '', phone)
    if len(digits) < 10:
        raise ValueError("Phone number must have at least 10 digits")
    if len(digits) > 15:
        raise ValueError("Phone number must have at most 15 digits")
    # Return last 10 digits for Indian numbers
    return digits[-10:] if len(digits) > 10 else digits
'''
    
    # Check if already added
    if 'def normalize_phone' not in content:
        # Find a good place to insert (after imports)
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('router = APIRouter()'):
                insert_pos = i
                break
        
        lines.insert(insert_pos, helper_function)
        content = '\n'.join(lines)
        print("✅ Added normalize_phone helper function")
    
    with open(visitor_routes_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def main():
    print("\n" + "="*60)
    print("  FIXING PROFILE UPDATE 409 CONFLICT ERROR")
    print("="*60 + "\n")
    
    # Fix the issues
    add_phone_normalization_helper()
    fix_profile_schema()
    fix_profile_update()
    
    print("\n" + "="*60)
    print("  FIXES APPLIED!")
    print("="*60)
    print("""
The following fixes were applied:

1. Phone number normalization - removes non-digits and standardizes to 10 digits
2. Duplicate phone check - only checks if phone is different from current
3. Better error messages - tells exactly which phone number is duplicated
4. Schema validation - validates phone format at the schema level

To apply fixes:
1. Restart your backend server
2. Test with a unique phone number (e.g., "9876543210")
3. Or update profile without changing phone number

Example payload that should work:
{
    "full_name": "Updated Name",
    "phone": "9876543210"  # Must be unique in the system
}
""")
    
    response = input("\nRestart backend now? (y/n): ").strip().lower()
    if response == 'y':
        import subprocess
        import sys
        print("\n🔄 Restarting backend...")
        subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"])
        print("✅ Backend restarting...")
    else:
        print("\nℹ️ Please restart your backend server manually.")


if __name__ == "__main__":
    main()