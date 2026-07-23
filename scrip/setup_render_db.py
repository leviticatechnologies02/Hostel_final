#!/usr/bin/env python3
"""
Setup Render PostgreSQL Database for Levitica Nestora

Run from project root:
    python scripts/setup_render_db.py

Or:
    cd D:\GIT HUB\hostel-management-api
    python scripts/setup_render_db.py
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    print(f"{RED}✗ {text}{RESET}")


def print_info(text):
    print(f"{BLUE}ℹ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_section(title):
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}{title:^70}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}\n")


# Render Database Configuration
RENDER_DATABASE_URL = "postgresql://leviticanestora_db_0hw4_user:OLTv0s0MZ4ff88BYqohgiceUJITTSnUgG@dpg-d7kaci4m0tmc73aeivm0-a.oregon-postgres.render.com/leviticanestora_db_0hw4"


def update_env_file():
    """Update .env file with Render database URL"""
    
    print_section("UPDATE .ENV FILE")
    
    env_path = project_root / ".env"
    
    # Backup existing .env
    if env_path.exists():
        backup_path = env_path.with_suffix('.env.backup')
        import shutil
        shutil.copy(env_path, backup_path)
        print_info(f"Backed up existing .env to {backup_path}")
    
    # Read existing .env to preserve other settings
    existing_config = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    existing_config[key] = value
    
    # Update DATABASE_URL
    existing_config['DATABASE_URL'] = RENDER_DATABASE_URL
    
    # Write back
    with open(env_path, 'w') as f:
        for key, value in existing_config.items():
            f.write(f"{key}={value}\n")
    
    print_success(f"Updated .env file with Render database URL")
    print_info(f"DATABASE_URL set to: {RENDER_DATABASE_URL[:60]}...")


def check_alembic():
    """Check if alembic is initialized"""
    
    alembic_dir = project_root / "alembic"
    alembic_versions = alembic_dir / "versions"
    
    if not alembic_dir.exists():
        print_error(f"Alembic directory not found at {alembic_dir}")
        print_info("Initializing alembic...")
        
        result = subprocess.run(
            ["alembic", "init", "alembic"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Failed to init alembic: {result.stderr}")
            return False
    
    if not alembic_versions.exists():
        alembic_versions.mkdir(parents=True)
    
    print_success(f"Alembic found at {alembic_dir}")
    return True


def run_migrations():
    """Run Alembic migrations"""
    
    print_section("RUNNING MIGRATIONS")
    
    # First, check if we have migration files
    alembic_versions = project_root / "alembic" / "versions"
    
    if not alembic_versions.exists() or not list(alembic_versions.glob("*.py")):
        print_warning("No migration files found. Creating initial migration...")
        
        # Create initial migration
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "initial_schema"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Failed to create migration: {result.stderr}")
            return False
        
        print_success("Created initial migration")
    
    # Run migrations
    print_info("Applying migrations to Render database...")
    
    # Set environment variable for alembic
    env = os.environ.copy()
    env['DATABASE_URL'] = RENDER_DATABASE_URL
    
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env
    )
    
    if result.returncode != 0:
        print_error(f"Migration failed: {result.stderr}")
        print_info("Trying with async method...")
        return run_migrations_async()
    
    print_success("Migrations completed successfully!")
    return True


async def run_migrations_async():
    """Run migrations using async SQLAlchemy"""
    
    print_info("Running migrations with async method...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.core.database import Base
        
        # Import all models
        import app.models.user
        import app.models.hostel
        import app.models.room
        import app.models.booking
        import app.models.student
        import app.models.payment
        import app.models.operations
        
        engine = create_async_engine(RENDER_DATABASE_URL, echo=True)
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print_success("Tables created successfully!")
        await engine.dispose()
        return True
        
    except Exception as e:
        print_error(f"Async migration failed: {str(e)}")
        return False


async def test_connection():
    """Test database connection"""
    
    print_section("TESTING CONNECTION")
    
    try:
        import asyncpg
        
        # Parse URL
        conn = await asyncpg.connect(RENDER_DATABASE_URL)
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        print_success(f"Connected to PostgreSQL!")
        print_info(f"Version: {version[:60]}...")
        
        # Check existing tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        if tables:
            print_success(f"Found {len(tables)} tables in database")
            print_info("Tables:")
            for table in tables[:15]:
                print(f"    - {table['tablename']}")
            if len(tables) > 15:
                print(f"    ... and {len(tables) - 15} more")
        else:
            print_warning("No tables found. Migrations may be needed.")
        
        await conn.close()
        return True
        
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")
        return False


async def verify_tables():
    """Verify that required tables exist"""
    
    print_section("VERIFYING TABLES")
    
    required_tables = [
        'users', 'hostels', 'rooms', 'beds',
        'bookings', 'students', 'payments',
        'complaints', 'notices', 'mess_menus'
    ]
    
    try:
        import asyncpg
        conn = await asyncpg.connect(RENDER_DATABASE_URL)
        
        existing_tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        existing = {row['tablename'] for row in existing_tables}
        
        missing = [t for t in required_tables if t not in existing]
        
        if missing:
            print_warning(f"Missing tables: {missing}")
            return False
        else:
            print_success("All required tables exist!")
            return True
            
    except Exception as e:
        print_error(f"Verification failed: {str(e)}")
        return False


def create_env_example():
    """Create .env.example file if not exists"""
    
    env_example_path = project_root / ".env.example"
    
    if not env_example_path.exists():
        example_content = """# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/leviticanestora_dev

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@leviticanestora.com

# Razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxx

# AWS S3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=leviticanestora-uploads
AWS_REGION=ap-south-1

# CORS
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
"""
        with open(env_example_path, 'w') as f:
            f.write(example_content)
        print_success("Created .env.example file")


async def main():
    """Main function"""
    
    print_section("LEVITICA_NESTORA - RENDER DATABASE SETUP")
    
    print_info(f"Project root: {project_root}")
    print_info(f"Database URL: {RENDER_DATABASE_URL[:60]}...")
    
    # Step 1: Test connection
    print_info("\nStep 1: Testing database connection...")
    connected = await test_connection()
    
    if not connected:
        print_error("\nCannot connect to Render database.")
        print_info("Possible issues:")
        print("  1. Database has expired (expires May 22, 2026)")
        print("  2. Password is incorrect")
        print("  3. SSL mode issue")
        print("  4. Your IP is not whitelisted")
        return
    
    # Step 2: Update .env
    print_info("\nStep 2: Updating .env file...")
    update_env_file()
    
    # Step 3: Create .env.example
    create_env_example()
    
    # Step 4: Create tables
    print_info("\nStep 3: Creating database tables...")
    
    # Try migrations first
    migration_success = run_migrations()
    
    if not migration_success:
        print_info("Migrations failed, trying direct table creation...")
        migration_success = await run_migrations_async()
    
    # Step 5: Verify tables
    print_info("\nStep 4: Verifying tables...")
    tables_ok = await verify_tables()
    
    # Step 6: Ask about seeding
    if tables_ok:
        print_section("SETUP COMPLETE")
        print_success("Render database is ready for use!")
        print_info("\nNext steps:")
        print("  1. Run migrations again if needed: alembic upgrade head")
        print("  2. Seed data: python -m scripts.seed_data")
        print("  3. Start the API: uvicorn app.main:app --reload")
        
        # Ask about seeding
        print(f"\n{BOLD}Would you like to seed initial data?{RESET}")
        response = input("(y/n) [default: n]: ").strip().lower()
        
        if response in ['y', 'yes']:
            print_info("Running seed data...")
            try:
                subprocess.run(
                    ["python", "-m", "scripts.seed_data"],
                    cwd=project_root,
                    check=True
                )
                print_success("Data seeded successfully!")
            except Exception as e:
                print_error(f"Seeding failed: {e}")
    else:
        print_error("Some tables are missing. Please check migration errors.")


if __name__ == "__main__":
    asyncio.run(main())