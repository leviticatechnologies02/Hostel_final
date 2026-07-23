import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def query_enum():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'roomtype'::regtype"))
        rows = result.fetchall()
        print('DB Enum values:', [r[0] for r in rows])

if __name__ == "__main__":
    asyncio.run(query_enum())
