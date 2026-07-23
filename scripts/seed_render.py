#!/usr/bin/env python3
"""
Seed script specifically for Render deployment.
Run this as a one-off command on Render.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.core.database import Base
from scripts.seed_data import Levitica NestoraSeeder

# Import all models so Base.metadata knows about them
import app.models.user
import app.models.hostel
import app.models.room
import app.models.booking
import app.models.student
import app.models.payment
import app.models.operations


async def seed_render():
    """Seed data on Render"""
    settings = get_settings()
    
    print(f"\n{'='*60}")
    print("  🌱 Seeding Levitica Nestora Database on Render")
    print(f"{'='*60}\n")
    print(f"Database URL: {settings.database_url[:50]}...\n")
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    # Create tables if they don't exist
    print("Creating tables if not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables ready\n")
    
    # Create session and run seeder
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        seeder = Levitica NestoraSeeder(session)
        await seeder.run()
    
    await engine.dispose()
    print("\n✅ Seeding complete!\n")


if __name__ == "__main__":
    asyncio.run(seed_render())