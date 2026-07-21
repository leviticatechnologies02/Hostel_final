"""
Clear ALL data from the database without dropping tables (schema is preserved).
Run: python -m scripts.clear_data  (from Hostel_final directory)

WARNING: This deletes EVERYTHING from the database permanently!
"""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

settings = get_settings()


async def clear_all_data():
    engine = create_async_engine(settings.database_url, echo=False)

    print("\n⚠️  WARNING: This will delete ALL data from the database!")
    confirm = input("Type 'YES' to confirm: ").strip()
    if confirm != "YES":
        print("❌ Aborted.")
        return

    async with engine.begin() as conn:
        print("\n🗑️  Clearing all data (truncating all tables)...")

        # Disable foreign key checks and truncate all data tables in dependency order
        await conn.execute(text("SET session_replication_role = 'replica';"))

        tables = [
            "payment_webhook_events",
            "payments",
            "attendance_records",
            "complaint_comments",
            "complaints",
            "maintenance_requests",
            "notices",
            "notice_reads",
            "mess_menu_items",
            "mess_menus",
            "waitlist_entries",
            "bed_stays",
            "booking_status_history",
            "bookings",
            "beds",
            "rooms",
            "students",
            "supervisor_hostel_mappings",
            "admin_hostel_mappings",
            "hostel_amenities",
            "hostel_images",
            "subscriptions",
            "hostels",
            "tokens",
            "users",
        ]

        for table in tables:
            try:
                await conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;'))
                print(f"  ✓ {table}")
            except Exception as e:
                print(f"  ⚠️  {table}: {e}")

        # Re-enable foreign key checks
        await conn.execute(text("SET session_replication_role = 'origin';"))

    await engine.dispose()
    print("\n✅ All data cleared! Database is now empty (tables/schema intact).")
    print("   You can now register new users and create real hostel data via the API.\n")


if __name__ == "__main__":
    asyncio.run(clear_all_data())
