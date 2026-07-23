"""
Reset database and re-seed from scratch.
Run: python -m scripts.reset_and_seed  (from hostel-management-api/)

WARNING: This drops ALL tables and recreates them. Use only in development.
"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.core.database import Base

# Import all models so Base.metadata knows about them
import app.models.user       # noqa: F401
import app.models.hostel     # noqa: F401
import app.models.room       # noqa: F401
import app.models.booking    # noqa: F401
import app.models.student    # noqa: F401
import app.models.payment    # noqa: F401
import app.models.operations # noqa: F401

from scripts.seed_data import Levitica NestoraSeeder

settings = get_settings()


async def _run():
    engine = create_async_engine(settings.database_url, echo=False)

    print("\n⚠️  Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✓ All tables dropped.")

    print("🔨 Creating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ All tables created.\n")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        seeder = Levitica NestoraSeeder(session)
        await seeder.run()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
