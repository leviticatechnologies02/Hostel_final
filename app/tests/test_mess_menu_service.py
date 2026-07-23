from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from fastapi import HTTPException
import pytest

from app.schemas.mess_menu import MessMenuCreateRequest
from app.services.mess_menu_service import MessMenuService


@pytest.mark.asyncio
async def test_list_supervisor_menus_returns_empty_without_assignment() -> None:
    session = AsyncMock()
    service = MessMenuService(session)
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=[]))

    result = await service.list_supervisor_menus(supervisor_id="sup-1")

    assert result == []


@pytest.mark.asyncio
async def test_create_admin_menu_commits_and_refreshes() -> None:
    session = AsyncMock()
    
    # Mock duplicate check to return no existing item
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=mock_result)
    
    service = MessMenuService(session)
    created_menu = SimpleNamespace(
        id="menu-1",
        hostel_id="hostel-1",
        week_start_date=date(2026, 3, 30),
        is_active=True,
        created_by="admin-1",
        created_at=None,
        updated_at=None
    )
    created_item = SimpleNamespace(
        id="item-1",
        day_of_week="Monday",
        meal_type="breakfast",
        item_name="Poha",
        is_veg=True,
        special_note=None
    )
    service.repository = SimpleNamespace(
        create_menu=AsyncMock(return_value=created_menu),
        create_item=AsyncMock(return_value=created_item),
    )

    result = await service.create_admin_menu(
        actor_id="admin-1",
        hostel_id="hostel-1",
        payload=MessMenuCreateRequest(
            week_start_date="2026-03-30",
            meal_type="breakfast",
            item_name="Poha",
            day_of_week="monday",
        ),
    )

    assert result["id"] == "item-1"
    assert result["item_name"] == "Poha"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_admin_menu_raises_conflict_on_duplicate() -> None:
    session = AsyncMock()
    
    # Mock duplicate check to return an existing item ID (simulate duplicate)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = "existing-item-id"
    session.execute = AsyncMock(return_value=mock_result)
    
    service = MessMenuService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_admin_menu(
            actor_id="admin-1",
            hostel_id="hostel-1",
            payload=MessMenuCreateRequest(
                week_start_date="2026-03-30",
                meal_type="breakfast",
                item_name="Poha",
                day_of_week="monday",
            ),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "A menu for this Meal Type already exists for the selected Week Start and Day. Please edit the existing menu instead."


