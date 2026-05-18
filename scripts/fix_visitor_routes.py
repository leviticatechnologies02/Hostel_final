# scripts/fix_visitor_routes.py
#!/usr/bin/env python3
"""
Quick fix script for visitor routes issues
"""

import os
import re

def fix_visitor_routes():
    """Fix visitor routes file"""
    file_path = "app/api/v1/visitor/routes.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Update the update_profile function to handle phone validation properly
    # Look for the update_profile function
    old_update = r'@router\.patch\("/profile".*?async def update_profile.*?\n(?:.*?\n)*?return user'
    
    # Fix 2: Update file size validation to return 400
    old_file_size = r'if payload\.file_size > 10 \* 1024 \* 1024:\s*\n\s*raise HTTPException\(\s*status_code=status\.HTTP_422_UNPROCESSABLE_ENTITY'
    new_file_size = 'if payload.file_size > 10 * 1024 * 1024:\n            raise HTTPException(\n                status_code=status.HTTP_400_BAD_REQUEST'
    
    content = re.sub(old_file_size, new_file_size, content)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed visitor routes file")
    return True

def fix_upload_schema():
    """Fix upload schema"""
    file_path = "app/schemas/upload.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if we need to update
    if 'le=10 * 1024 * 1024' in content:
        # Replace with version without le constraint
        new_content = '''from pydantic import BaseModel, Field, field_validator


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=120)
    file_size: int = Field(gt=0)

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("File size must be greater than 0")
        return v


class PresignedUploadResponse(BaseModel):
    upload_url: str
    file_url: str
    filename: str
'''
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Fixed upload schema")
    else:
        print("ℹ Upload schema already fixed")
    
    return True

def fix_profile_schema():
    """Fix visitor profile update schema"""
    # Check if the schema is in a separate file or in routes
    file_path = "app/api/v1/visitor/routes.py"
    
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update the VisitorProfileUpdateRequest class
    old_class = r'class VisitorProfileUpdateRequest\(BaseModel\):.*?\n(?:.*?\n)*?    profile_picture_url: str \| None = None'
    
    new_class = '''class VisitorProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None)  # Validation done in service
    profile_picture_url: str | None = None
    
    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str | None) -> str | None:
        """Basic phone format validation"""
        if v is None:
            return v
        # Remove non-digits
        digits = re.sub(r'[^0-9]', '', v)
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        if len(digits) > 15:
            raise ValueError("Phone number must have at most 15 digits")
        return digits[-10:] if len(digits) > 10 else digits'''
    
    # Only replace if the old pattern exists
    if 'class VisitorProfileUpdateRequest' in content:
        # Import field_validator and re if not present
        if 'from pydantic import Field, field_validator' not in content:
            content = content.replace(
                'from pydantic import BaseModel, Field',
                'from pydantic import BaseModel, Field, field_validator'
            )
        
        # Add import re if not present
        if 'import re' not in content[:500]:
            content = content.replace(
                'from pydantic import BaseModel, Field, field_validator\n',
                'from pydantic import BaseModel, Field, field_validator\nimport re\n'
            )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed profile schema")
    
    return True

def restart_backend():
    """Restart the backend server"""
    import subprocess
    import signal
    import time
    
    print("\n🔄 Restarting backend server...")
    
    # Find and kill existing uvicorn process
    try:
        result = subprocess.run(
            'taskkill /f /im python.exe', 
            shell=True, 
            capture_output=True
        )
        time.sleep(2)
    except:
        pass
    
    # Start new server
    print("🚀 Starting backend server...")
    subprocess.Popen(
        'python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000',
        shell=True
    )
    
    print("✅ Backend server restarted")
    print("⏳ Waiting for server to start...")
    time.sleep(5)

if __name__ == "__main__":
    print("="*60)
    print("  FIXING VISITOR ROUTES ISSUES")
    print("="*60)
    
    fix_visitor_routes()
    fix_upload_schema()
    fix_profile_schema()
    
    print("\n" + "="*60)
    print("  FIXES APPLIED!")
    print("="*60)
    print("\nTo apply fixes:")
    print("1. Restart your backend server")
    print("2. Run the test again: python scripts/test_visitor_routes_comprehensive.py")
    
    # Ask if user wants to restart
    response = input("\nRestart backend now? (y/n): ").strip().lower()
    if response == 'y':
        restart_backend()