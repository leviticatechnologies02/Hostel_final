import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def alter_enum():
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("ALTER TYPE roomtype ADD VALUE IF NOT EXISTS 'FIVE_BED'"))
            await session.execute(text("ALTER TYPE roomtype ADD VALUE IF NOT EXISTS 'SIX_BED'"))
            await session.commit()
            print('Successfully added FIVE_BED and SIX_BED to roomtype enum')
        except Exception as e:
            print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(alter_enum())
