# app/core/database.py - FIXED VERSION

from collections.abc import AsyncGenerator
import ssl
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text  # Add this import
from app.config import get_settings
import asyncio

settings = get_settings()

# Configure SSL for asyncpg - Render PostgreSQL requires SSL
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Create engine with OPTIMIZED settings for remote database
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Disable echo for production
    future=True,
    pool_size=5,  # Smaller pool for remote connection
    max_overflow=10,
    pool_timeout=30,  # Longer timeout for remote
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections every hour
    connect_args={
        "ssl": ssl_context,
        "server_settings": {
            "application_name": "stayease_api",
            "statement_timeout": "30000",  # 30 second statement timeout
            "idle_in_transaction_session_timeout": "60000",  # 60 second idle timeout
        },
        "timeout": 30,  # Connection timeout
        "command_timeout": 30,  # Command timeout
    }
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            # Set a timeout for the session - FIXED: Use text() wrapper
            await session.execute(text("SET statement_timeout = '30000'"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()