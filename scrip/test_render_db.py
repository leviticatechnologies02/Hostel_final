#!/usr/bin/env python3
"""
Test Render PostgreSQL Database Connection

Run from project root:
    python scripts/test_render_db.py
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
import asyncio
import ssl

# Render Database Configuration (from your screenshot)
# Note: The password appears to be: 0L7DvsoMZ4ff88BYqohgiceUJITTSmJG
RENDER_PASSWORD = "0L7DvsoMZ4ff88BYqohgiceUJITTSmJG"
RENDER_HOST = "dpg-d7kaci4m0tmc73aeivm0-a.oregon-postgres.render.com"
RENDER_DATABASE = "leviticanestora_db_0hw4"
RENDER_USER = "leviticanestora_db_0hw4_user"
RENDER_PORT = 5432

# Connection URL with SSL (REQUIRED for Render)
RENDER_DATABASE_URL = f"postgresql://{RENDER_USER}:{RENDER_PASSWORD}@{RENDER_HOST}:{RENDER_PORT}/{RENDER_DATABASE}"

# Alternative connection config for asyncpg
RENDER_CONFIG = {
    "host": RENDER_HOST,
    "port": RENDER_PORT,
    "database": RENDER_DATABASE,
    "user": RENDER_USER,
    "password": RENDER_PASSWORD,
    "ssl": True  # SSL required
}

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
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
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{title:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


async def test_render_connection():
    """Test connection to Render PostgreSQL database"""
    
    print_section("RENDER DATABASE CONNECTION TEST")
    
    # Test with SSL
    print_info("Testing External Database URL with SSL...")
    conn = None
    try:
        # Create SSL context
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        conn = await asyncpg.connect(
            host=RENDER_HOST,
            port=RENDER_PORT,
            database=RENDER_DATABASE,
            user=RENDER_USER,
            password=RENDER_PASSWORD,
            ssl=ssl_ctx
        )
        
        print_success("Connected to Render database successfully with SSL!")
        
        # Test query - use a function that exists in PostgreSQL 18
        version = await conn.fetchval("SELECT version()")
        print_info(f"PostgreSQL Version: {version[:80]}...")
        
        # Check current database
        current_db = await conn.fetchval("SELECT current_database()")
        print_info(f"Current Database: {current_db}")
        
        # Check current user
        current_user = await conn.fetchval("SELECT current_user")
        print_info(f"Current User: {current_user}")
        
        # List all tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        if tables:
            print_success(f"Found {len(tables)} tables in database")
            print_info("Tables in database:")
            for table in tables[:15]:
                print(f"    - {table['tablename']}")
            if len(tables) > 15:
                print(f"    ... and {len(tables) - 15} more")
        else:
            print_warning("No tables found in database. You may need to run migrations.")
        
        # Count users if users table exists
        users_exists = any(t['tablename'] == 'users' for t in tables)
        if users_exists:
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            print_success(f"Total users: {user_count}")
        else:
            print_warning("No users table found. Run migrations first.")
        
        await conn.close()
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print_error("Invalid password! Please check the database password.")
        return False
    except Exception as e:
        print_error(f"Failed to connect: {str(e)}")
        return False
    finally:
        if conn and not conn.is_closed():
            await conn.close()


def show_connection_info():
    """Display connection information"""
    
    print_section("CONNECTION INFORMATION")
    
    print(f"{BOLD}Render Database Details:{RESET}")
    print(f"  Host: {RENDER_HOST}")
    print(f"  Port: {RENDER_PORT}")
    print(f"  Database: {RENDER_DATABASE}")
    print(f"  Username: {RENDER_USER}")
    print(f"  Password: {RENDER_PASSWORD[:10]}...{RENDER_PASSWORD[-5:]} (hidden)")
    
    print(f"\n{BOLD}Connection URLs (with SSL):{RESET}")
    print(f"  External: {RENDER_DATABASE_URL}")
    
    print(f"\n{BOLD}SSL Requirements:{RESET}")
    print(f"  ✅ SSL is REQUIRED for Render PostgreSQL")
    print(f"  ✅ Add ?sslmode=require to connection string")
    print(f"  ✅ Or use sslmode=verify-full for production")
    
    print(f"\n{BOLD}Important Notes:{RESET}")
    print(f"  ⚠ Database expires on: {YELLOW}May 22, 2026{RESET}")
    print(f"  ⚠ Storage limit: 1 GB")
    print(f"  ℹ Region: Oregon (US West)")
    print(f"  ℹ PostgreSQL Version: 18")


def show_psql_command():
    """Show psql command for testing"""
    
    print_section("PSQL COMMAND")
    
    print(f"ℹ Test connection with psql:")
    print(f'  PGPASSWORD={RENDER_PASSWORD} psql -h {RENDER_HOST} -U {RENDER_USER} -d {RENDER_DATABASE} -c "SELECT version();"')
    
    print(f"\nℹ Connect interactively:")
    print(f'  PGPASSWORD={RENDER_PASSWORD} psql -h {RENDER_HOST} -U {RENDER_USER} -d {RENDER_DATABASE}')


async def update_env_file():
    """Update .env file with Render database URL"""
    
    print_section("UPDATE .ENV FILE")
    
    env_path = project_root / ".env"
    
    # Create .env content with Render database
    env_content = f"""# Render PostgreSQL Database
DATABASE_URL={RENDER_DATABASE_URL}

# Redis Configuration (for Celery) - Update with your Redis URL
REDIS_URL=redis://localhost:6379/0

# Security Configuration
SECRET_KEY=your-secret-key-change-this-in-production-{os.urandom(16).hex()}
JWT_ALGORITHM=HS256
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Email Configuration (Update with your email settings)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@leviticanestora.com

# Razorpay Payment Gateway (Test Mode)
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxx

# AWS S3 File Storage (Optional)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=leviticanestora-uploads
AWS_REGION=ap-south-1

# CORS Configuration
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
"""
    
    # Backup existing .env if it exists
    if env_path.exists():
        backup_path = env_path.with_suffix('.env.backup')
        env_path.rename(backup_path)
        print_info(f"Backed up existing .env to {backup_path}")
    
    # Write new .env file
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print_success(f"Created/Updated .env file at {env_path}")
    print_warning("Please update email, Razorpay, and other credentials in .env file")


async def run_migrations():
    """Run Alembic migrations on Render database"""
    
    print_section("RUN MIGRATIONS")
    
    try:
        # Set environment variable for database URL
        os.environ["DATABASE_URL"] = RENDER_DATABASE_URL
        
        # Import alembic after path is set
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config(project_root / "alembic.ini")
        # Update the SQLAlchemy URL in alembic.ini
        alembic_cfg.set_main_option("sqlalchemy.url", RENDER_DATABASE_URL)
        
        print_info("Running migrations...")
        command.upgrade(alembic_cfg, "head")
        print_success("Migrations completed successfully!")
        
    except Exception as e:
        print_error(f"Migration failed: {str(e)}")
        print_info("You can also run: alembic upgrade head")


async def main():
    """Main function"""
    
    print_section("LEVITICA_NESTORA - RENDER DATABASE SETUP")
    
    # Show connection info
    show_connection_info()
    
    # Show psql command
    show_psql_command()
    
    # Test connection
    connected = await test_render_connection()
    
    if not connected:
        print_error("\n❌ Cannot connect to Render database.")
        print("\nTroubleshooting steps:")
        print("  1. Make sure SSL is enabled: ?sslmode=require")
        print("  2. Check if your IP is whitelisted in Render dashboard")
        print("     - Go to Render Dashboard → Your Database → Settings")
        print("     - Add your public IP to 'Allow List'")
        print("  3. Verify database password is correct")
        print("  4. Check if database is still active (expires May 22, 2026)")
        print("  5. Try connecting with psql first to isolate the issue")
        return
    
    # Ask user what to do
    print(f"\n{BOLD}What would you like to do?{RESET}")
    print("  1. Update .env file with Render database URL")
    print("  2. Run migrations only")
    print("  3. Run migrations and seed data")
    print("  4. Run seed data only (after migrations)")
    print("  5. Skip (just test connection)")
    
    choice = input(f"\n{BOLD}Enter choice (1-5) [default: 5]: {RESET}").strip()
    
    if choice == "1":
        await update_env_file()
    elif choice == "2":
        await run_migrations()
    elif choice == "3":
        await run_migrations()
        # Ask if they want to seed data
        seed_choice = input(f"\n{BOLD}Run seed data? (y/n) [default: n]: {RESET}").strip().lower()
        if seed_choice == 'y':
            await seed_data()
    elif choice == "4":
        await seed_data()
    else:
        print_info("Skipping additional setup")
    
    print_section("COMPLETE")
    print_success("Render database is ready for use!")
    print_info(f"Database: {RENDER_DATABASE}")
    print_info(f"Host: {RENDER_HOST}")

async def seed_data():
    """Seed initial data into Render database"""
    
    print_section("SEED DATA")
    
    try:
        # Import seeder after path is set
        from scripts.seed_data import LeviticaNestoraSeeder
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        print_info("Creating database engine...")
        engine = create_async_engine(RENDER_DATABASE_URL, echo=False)
        
        print_info("Creating session...")
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # Run seeding
        async with async_session() as session:
            seeder = LeviticaNestoraSeeder(session)
            await seeder.run()
        
        await engine.dispose()
        print_success("Data seeded successfully!")
        
    except Exception as e:
        print_error(f"Seeding failed: {str(e)}")
        print_info("You can also run: python -m scripts.seed_data --clean")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())