import asyncio
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.hostel import AdminHostelMapping
from app.models.operations import Notice

async def delete_all_admins():
    async with AsyncSessionLocal() as session:
        # Get all hostel admin IDs
        result = await session.execute(
            select(User.id).where(User.role == UserRole.HOSTEL_ADMIN)
        )
        admin_ids = result.scalars().all()
        
        if admin_ids:
            # First, delete notices created by these admins
            await session.execute(
                delete(Notice).where(Notice.created_by.in_(admin_ids))
            )
            
            # Second, delete hostel mappings
            await session.execute(
                delete(AdminHostelMapping).where(AdminHostelMapping.admin_id.in_(admin_ids))
            )
            
            # Now delete the admins
            result = await session.execute(
                select(User).where(User.id.in_(admin_ids))
            )
            admins = result.scalars().all()
            
            count = 0
            for admin in admins:
                await session.delete(admin)
                count += 1
                print(f"Deleted admin: {admin.full_name} ({admin.email})")
                
            await session.commit()
            print(f"Successfully deleted {count} hostel admins and all related data.")
        else:
            print("No hostel admins found.")

if __name__ == "__main__":
    asyncio.run(delete_all_admins())
