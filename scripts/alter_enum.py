import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def alter_enum():
    async with AsyncSessionLocal() as session:
        try:
            # We must use execute() and set autocommit because ALTER TYPE cannot run inside a transaction block
            # Actually, asyncpg connection has an execute method we can use, but SQLAlchemy 2.0 connection works too
            # Let's use raw connection if possible, or try with session:
            await session.execute(text("ALTER TYPE roomtype ADD VALUE IF NOT EXISTS 'quadruple'"))
            await session.commit()
            print('Successfully added quadruple to roomtype enum')
        except Exception as e:
            print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(alter_enum())
