import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def fix_room_types():
    async with AsyncSessionLocal() as session:
        try:
            # We must use execute() and set autocommit because ALTER TYPE cannot run inside a transaction block
            # Actually, asyncpg connection has an execute method we can use, but SQLAlchemy 2.0 connection works too
            # Let's use raw connection if possible, or try with session:
            await session.execute(text("UPDATE rooms SET room_type = 'QUADRUPLE' WHERE room_type = 'quadruple'"))
            await session.commit()
            print('Successfully updated rooms with lowercase quadruple to uppercase QUADRUPLE')
        except Exception as e:
            print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(fix_room_types())
