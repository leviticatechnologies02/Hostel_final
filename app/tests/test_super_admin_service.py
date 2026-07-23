from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.hostel import HostelStatus
from app.services.super_admin_service import SuperAdminService
from app.schemas.super_admin import AssignHostelsRequest, SuperAdminAdminCreateRequest, SuperAdminHostelCreateRequest


@pytest.mark.asyncio
async def test_get_dashboard_aggregates_counts() -> None:
    session = AsyncMock()
    service = SuperAdminService(session)
    service.repository = SimpleNamespace(
        count_hostels=AsyncMock(return_value=5),
        count_admins=AsyncMock(return_value=2),
        count_subscriptions=AsyncMock(return_value=4),
    )

    result = await service.get_dashboard()

    assert result.hostels == 5
    assert result.admins == 2
    assert result.subscriptions == 4


@pytest.mark.asyncio
async def test_create_hostel_commits_and_refreshes() -> None:
    session = AsyncMock()
    service = SuperAdminService(session)
    created = SimpleNamespace(id="hostel-1")
    service.repository = SimpleNamespace(create_hostel=AsyncMock(return_value=created))

    result = await service.create_hostel(
        SuperAdminHostelCreateRequest(
            name="Levitica Nestora One",
            slug="leviticanestora-one",
            description="A managed hostel property for students.",
            hostel_type="boys",
            address_line1="Street 1",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            latitude=18.52,
            longitude=73.85,
            phone="9999999999",
            email="hostel@example.com",
        )
    )

    assert result == created
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created)


@pytest.mark.asyncio
async def test_create_admin_commits_and_refreshes() -> None:
    session = AsyncMock()
    service = SuperAdminService(session)
    created = SimpleNamespace(id="admin-1")
    service.repository = SimpleNamespace(create_admin=AsyncMock(return_value=created))

    result = await service.create_admin(
        SuperAdminAdminCreateRequest(
            email="admin@example.com",
            phone="9999999998",
            full_name="Admin User",
            password="Password123",
        )
    )

    assert result == created
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created)


@pytest.mark.asyncio
async def test_assign_hostels_replaces_existing_mappings() -> None:
    session = AsyncMock()
    service = SuperAdminService(session)
    service.repository = SimpleNamespace(
        get_admin_by_id=AsyncMock(return_value=SimpleNamespace(id="admin-1")),
        replace_admin_hostels=AsyncMock(),
    )

    result = await service.assign_hostels(
        actor_id="super-admin-1",
        admin_id="admin-1",
        payload=AssignHostelsRequest(hostel_ids=["hostel-1", "hostel-2"]),
    )

    assert result["admin_id"] == "admin-1"
    service.repository.replace_admin_hostels.assert_awaited_once_with(
        admin_id="admin-1",
        hostel_ids=["hostel-1", "hostel-2"],
        assigned_by="super-admin-1",
    )
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_hostel_status_commits() -> None:
    session = AsyncMock()
    hostel = SimpleNamespace(id="hostel-1", status=HostelStatus.PENDING_APPROVAL)
    service = SuperAdminService(session)
    service.repository = SimpleNamespace(get_hostel_by_id=AsyncMock(return_value=hostel))

    result = await service.update_hostel_status("hostel-1", HostelStatus.ACTIVE)

    assert result.status == HostelStatus.ACTIVE
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(hostel)
