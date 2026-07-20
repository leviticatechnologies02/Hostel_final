from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base
from app.models.hostel import AdminHostelMapping, Hostel, HostelStatus, HostelType
from app.models.operations import Subscription
from app.models.user import User, UserRole


class SuperAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_hostels(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Hostel))
        return int(result.scalar_one() or 0)

    async def count_admins(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.HOSTEL_ADMIN)
        )
        return int(result.scalar_one() or 0)

    async def count_subscriptions(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Subscription))
        return int(result.scalar_one() or 0)

    async def list_hostels(self, *, status: str | None = None) -> list[Hostel]:
        from sqlalchemy.orm import selectinload
        query = select(Hostel).options(
            selectinload(Hostel.images),
            selectinload(Hostel.admin_mappings).selectinload(AdminHostelMapping.admin)
        )
        if status:
            try:
                status_enum = HostelStatus(status)
                query = query.where(Hostel.status == status_enum)
            except ValueError:
                pass
        
        result = await self.session.execute(query.order_by(Hostel.created_at.desc()))
        return list(result.scalars().all())

    async def list_hostels_paginated(
        self, *, status: str | None = None, page: int = 1, per_page: int = 20
    ) -> tuple[list[Hostel], int]:
        from sqlalchemy.orm import selectinload
        from app.models.hostel import AdminHostelMapping
        query = select(Hostel).options(
            selectinload(Hostel.images),
            selectinload(Hostel.admin_mappings).selectinload(AdminHostelMapping.admin)
        )
        count_query = select(func.count()).select_from(Hostel)
        if status:
            try:
                status_enum = HostelStatus(status)
                query = query.where(Hostel.status == status_enum)
                count_query = count_query.where(Hostel.status == status_enum)
            except ValueError:
                pass
        query = query.order_by(Hostel.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        hostels_result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return list(hostels_result.scalars().all()), int(total_result.scalar_one() or 0)

    async def create_hostel(self, hostel: Hostel) -> Hostel:
        self.session.add(hostel)
        await self.session.flush()
        return hostel

    async def get_hostel_by_id(self, hostel_id: str) -> Hostel | None:
        from sqlalchemy.orm import selectinload
        from app.models.hostel import AdminHostelMapping
        query = select(Hostel).options(
            selectinload(Hostel.images),
            selectinload(Hostel.admin_mappings).selectinload(AdminHostelMapping.admin)
        ).where(Hostel.id == hostel_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_hostel(self, hostel: Hostel) -> None:
        """Hard-delete a hostel and all its cascade-dependent records."""
        await self.session.delete(hostel)
        await self.session.flush()

    async def list_admins(self) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.role == UserRole.HOSTEL_ADMIN).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_admin(self, admin: User) -> User:
        self.session.add(admin)
        await self.session.flush()
        return admin

    async def get_admin_by_id(self, admin_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == admin_id, User.role == UserRole.HOSTEL_ADMIN)
        )
        return result.scalar_one_or_none()

    async def replace_admin_hostels(self, admin_id: str, hostel_ids: list[str], assigned_by: str) -> None:
        await self.session.execute(delete(AdminHostelMapping).where(AdminHostelMapping.admin_id == admin_id))
        for index, hostel_id in enumerate(hostel_ids):
            self.session.add(
                AdminHostelMapping(
                    admin_id=admin_id,
                    hostel_id=hostel_id,
                    is_primary=index == 0,
                    assigned_by=assigned_by,
                )
            )
        await self.session.flush()

    async def list_subscriptions(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription).order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())



    async def get_subscription_by_id(self, subscription_id: str) -> Subscription | None:
        """Get a single subscription by ID."""
        from app.models.operations import Subscription
        from sqlalchemy import select
        result = await self.session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()


    async def get_subscription_by_hostel_id(self, hostel_id: str) -> Subscription | None:
        """Get active subscription for a hostel."""
        from app.models.operations import Subscription
        from sqlalchemy import select
        result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.hostel_id == hostel_id,
                Subscription.status == "active"
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


    async def create_subscription_record(self, subscription: Subscription) -> Subscription:
        """Create a new subscription record."""
        self.session.add(subscription)
        await self.session.flush()
        return subscription


    async def update_subscription_record(self, subscription: Subscription) -> Subscription:
        """Update an existing subscription."""
        await self.session.flush()
        return subscription


    async def delete_subscription_record(self, subscription: Subscription) -> None:
        """Delete a subscription record."""
        await self.session.delete(subscription)
        await self.session.flush()