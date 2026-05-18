# FILE: app/services/maintenance_service.py

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import MaintenanceRequest
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.maintenance_repository import MaintenanceRepository
from app.schemas.maintenance import MaintenanceCreateRequest, MaintenanceUpdateRequest

# Valid statuses for maintenance requests
VALID_STATUSES = {"open", "in_progress", "completed", "cancelled", "approved"}


def validate_status_transition(current_status: str, new_status: str) -> bool:
    """Validate allowed status transitions for maintenance requests."""
    allowed_transitions = {
        "open": ["approved", "in_progress", "cancelled"],
        "pending_approval": ["approved", "cancelled"],
        "approved": ["in_progress", "cancelled"],
        "in_progress": ["completed", "cancelled"],
        "completed": ["cancelled"],  # Or maybe completed is terminal
        "cancelled": [],  # Terminal state - no transitions
    }
    
    valid_next_statuses = allowed_transitions.get(current_status, [])
    if new_status not in valid_next_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current_status}' to '{new_status}'. "
                   f"Allowed transitions: {valid_next_statuses}"
        )
    return True



class MaintenanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.maintenance = MaintenanceRepository(session)
        self.assignments = AssignmentRepository(session)

    def _validate_status(self, status: str) -> str:
        """Validate status value and return normalized version"""
        if status is None:
            return None
        normalized = status.lower().strip()
        if normalized not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}. Got: '{status}'"
            )
        return normalized

    async def list_supervisor_requests(self, *, supervisor_id: str):
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        requests: list[MaintenanceRequest] = []
        for hostel_id in hostel_ids:
            requests.extend(await self.maintenance.list_by_hostel(hostel_id))
        return requests

    async def create_supervisor_request(
        self, *, supervisor_id: str, payload: MaintenanceCreateRequest
    ) -> MaintenanceRequest:
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        if not hostel_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hostel assigned.")

        requires_admin_approval = (
            payload.estimated_cost is not None and payload.estimated_cost >= 5000
        )
        
        # If approval is required, set status to "pending_approval" initially
        initial_status = "pending_approval" if requires_admin_approval else "open"
        
        request = MaintenanceRequest(
            hostel_id=hostel_ids[0],
            room_id=payload.room_id,
            reported_by=supervisor_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status=initial_status,
            estimated_cost=payload.estimated_cost,
            requires_admin_approval=requires_admin_approval,
        )
        request = await self.maintenance.create(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request
        
        
    async def update_supervisor_request(
        self, *, supervisor_id: str, request_id: str, payload: MaintenanceUpdateRequest
    ) -> MaintenanceRequest:
        request = await self.maintenance.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        if str(request.hostel_id) not in hostel_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hostel access.")

        # Validate status transition if status is being changed
        if payload.status is not None:
            current_status = request.status
            new_status = payload.status.lower().strip()
            
            # Validate allowed transitions
            validate_status_transition(current_status, new_status)
            
            request.status = new_status
        else:
            # Only update other fields if status not provided
            if payload.estimated_cost is not None:
                request.estimated_cost = payload.estimated_cost
            if payload.actual_cost is not None:
                request.actual_cost = payload.actual_cost
            if payload.assigned_vendor_name is not None:
                request.assigned_vendor_name = payload.assigned_vendor_name
            if payload.vendor_contact is not None:
                request.vendor_contact = payload.vendor_contact
            if payload.requires_admin_approval is not None:
                request.requires_admin_approval = payload.requires_admin_approval
        
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def approve_admin_request(self, *, actor_id: str, request_id: str) -> MaintenanceRequest:
        request = await self.maintenance.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
        
        # Only allow approval if request is in pending_approval status or open (based on your workflow)
        # Based on the test, open status should NOT be approvable
        if request.status not in ["pending_approval"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve request in '{request.status}' status. Only 'pending_approval' requests can be approved."
            )
        
        if not request.requires_admin_approval:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This request does not require admin approval."
            )
        
        request.requires_admin_approval = False
        request.approved_by = actor_id
        request.status = "approved"  # or "in_progress" - choose appropriate status
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def list_admin_requests(self, *, hostel_id: str):
        """List maintenance requests for admin view."""
        return await self.maintenance.list_by_hostel(hostel_id)

    async def update_admin_request(
        self, *, admin_id: str, request_id: str, payload: MaintenanceUpdateRequest
    ) -> MaintenanceRequest:
        """
        Admin update for maintenance requests.
        Admins can approve requests (change from pending_approval to approved)
        or update any request in their hostel.
        """
        request = await self.maintenance.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
        
        new_status = payload.status.lower().strip() if payload.status else None
        
        # Handle approval separately
        if new_status == "approved":
            return await self.approve_admin_request(actor_id=admin_id, request_id=request_id)
        
        # For other updates, check if status transition is valid
        current_status = request.status
        requires_approval = request.requires_admin_approval
        
        allowed_transitions = {
            "open": ["in_progress", "cancelled", "pending_approval"],
            "pending_approval": ["approved", "cancelled"],
            "approved": ["in_progress", "cancelled"],
            "in_progress": ["completed", "cancelled"],
            "completed": [],  # Terminal state
            "cancelled": [],  # Terminal state
        }
        
        if new_status and new_status not in allowed_transitions.get(current_status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from '{current_status}' to '{new_status}'. "
                       f"Allowed: {allowed_transitions.get(current_status, [])}"
            )
        
        # Apply updates
        if new_status:
            request.status = new_status
        
        if payload.estimated_cost is not None:
            request.estimated_cost = payload.estimated_cost
        if payload.actual_cost is not None:
            request.actual_cost = payload.actual_cost
        if payload.assigned_vendor_name is not None:
            request.assigned_vendor_name = payload.assigned_vendor_name
        if payload.vendor_contact is not None:
            request.vendor_contact = payload.vendor_contact
        if payload.requires_admin_approval is not None:
            request.requires_admin_approval = payload.requires_admin_approval
        
        if new_status == "completed" and request.completed_at is None:
            from datetime import datetime, timezone
            request.completed_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(request)
        return request
