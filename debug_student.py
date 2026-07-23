import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.student import Student

async def debug():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.email).join(Student, Student.user_id == User.id).limit(5)
        )
        emails = result.scalars().all()
        print(f"Valid student emails: {emails}")

if __name__ == "__main__":
    asyncio.run(debug())
