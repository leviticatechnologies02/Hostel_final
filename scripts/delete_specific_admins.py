import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def delete_specific_admins():
    names_to_delete = [
        "ruthvik vemula",
        "Sanvi Reddy"
    ]
    
    async with AsyncSessionLocal() as session:
        for name in names_to_delete:
            result = await session.execute(select(User).where(User.full_name == name))
            user = result.scalar_one_or_none()
            if user:
                await session.delete(user)
                print(f"Deleted user: {user.full_name} ({user.email})")
            else:
                print(f"User not found: {name}")
        
        await session.commit()
        print("Done deleting specified admins.")

if __name__ == "__main__":
    asyncio.run(delete_specific_admins())
