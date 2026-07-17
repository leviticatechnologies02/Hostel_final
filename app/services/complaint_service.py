import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.complaint_sla import compute_sla_deadline, is_sla_breached
from app.models.operations import Complaint
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import ComplaintCreateRequest, ComplaintResponse, ComplaintUpdateRequest


class ComplaintService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.complaints = ComplaintRepository(session)
        self.assignments = AssignmentRepository(session)

    def _to_response(self, c: Complaint) -> ComplaintResponse:
        deadline = compute_sla_deadline(c.created_at, c.priority)
        breached = is_sla_breached(
            status=c.status,
            created_at=c.created_at,
            priority=c.priority,
            resolved_at=c.resolved_at,
        )
        return ComplaintResponse(
            id=str(c.id),
            complaint_number=c.complaint_number,
            student_id=str(c.student_id),
            hostel_id=str(c.hostel_id),
            category=c.category,
            title=c.title,
            description=c.description,
            priority=c.priority,
            status=c.status,
            assigned_to=str(c.assigned_to) if c.assigned_to else None,
            photo_url=c.photo_url,
            resolution_notes=c.resolution_notes,
            resolved_at=c.resolved_at,
            sla_deadline=deadline,
            sla_breached=breached,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )

    async def list_student_complaints(self, *, user_id: str) -> list[ComplaintResponse]:
        student = await self.assignments.get_student_by_user(user_id)
        if student is None:
            return []
        rows = await self.complaints.list_by_student(str(student.id))
        return [self._to_response(c) for c in rows]

    async def create_student_complaint(self, *, user_id: str, payload: ComplaintCreateRequest) -> ComplaintResponse:
        student = await self.assignments.get_student_by_user(user_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found.")

        complaint = Complaint(
            complaint_number=f"CMP-{uuid.uuid4().hex[:8].upper()}",
            student_id=student.id,
            hostel_id=student.hostel_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status="open",
            photo_url=payload.photo_url,
        )
        complaint = await self.complaints.create(complaint)
        await self.session.commit()
        await self.session.refresh(complaint)
        return self._to_response(complaint)

    async def list_supervisor_complaints(self, *, supervisor_id: str) -> list[ComplaintResponse]:
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        all_complaints: list[Complaint] = []
        for hostel_id in hostel_ids:
            all_complaints.extend(await self.complaints.list_by_hostel(hostel_id))
        return [self._to_response(c) for c in all_complaints]

    async def update_supervisor_complaint(
        self, *, supervisor_id: str, complaint_id: str, payload: ComplaintUpdateRequest
    ) -> ComplaintResponse:
        complaint = await self.complaints.get_by_id(complaint_id)
        if complaint is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found.")
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        if str(complaint.hostel_id) not in hostel_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hostel access.")

        if payload.status is not None:
            complaint.status = payload.status
        if payload.assigned_to is not None:
            complaint.assigned_to = payload.assigned_to
        if payload.resolution_notes is not None:
            complaint.resolution_notes = payload.resolution_notes
        if payload.status is not None and payload.status.lower() in ("resolved", "closed"):
            from datetime import datetime, timezone

            if complaint.resolved_at is None:
                complaint.resolved_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(complaint)
        return self._to_response(complaint)

    async def list_admin_complaints(
        self,
        *,
        hostel_id: str,
        priority: str | None = None,
        sla_filter: str | None = None,
    ) -> list[ComplaintResponse]:
        rows = await self.complaints.list_by_hostel(hostel_id)
        out = [self._to_response(c) for c in rows]
        if priority:
            p = priority.strip().lower()
            out = [x for x in out if x.priority.lower() == p]
        if sla_filter and sla_filter.lower() in ("breached", "ok"):
            want_breach = sla_filter.lower() == "breached"
            out = [x for x in out if x.sla_breached == want_breach]
        return out

    async def update_admin_complaint(
        self, *, hostel_id: str, complaint_id: str, payload: ComplaintUpdateRequest
    ) -> ComplaintResponse:
        complaint = await self.complaints.get_by_id(complaint_id)
        if complaint is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found.")
        if str(complaint.hostel_id) != hostel_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hostel access.")

        if payload.status is not None:
            complaint.status = payload.status
        if payload.assigned_to is not None:
            complaint.assigned_to = payload.assigned_to
        if payload.resolution_notes is not None:
            complaint.resolution_notes = payload.resolution_notes
        if payload.status is not None and payload.status.lower() in ("resolved", "closed"):
            from datetime import datetime, timezone

            if complaint.resolved_at is None:
                complaint.resolved_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(complaint)
        return self._to_response(complaint)



    async def delete_complaint(
        self,
        *,
        complaint_id: str,
        user_role: str,
        user_hostel_ids: set[str],
    ) -> bool:
        """
        Delete a complaint with permission check.
        
        Args:
            complaint_id: ID of complaint to delete
            user_role: Role of the user (admin, supervisor, etc.)
            user_hostel_ids: Hostel IDs the user has access to
        
        Returns:
            True if deleted, False if not found
        """
        complaint = await self.complaints.get_by_id(complaint_id)
        
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Complaint not found."
            )
        
        # Super admin can delete any complaint
        if user_role != "super_admin":
            # Check if user has access to this hostel
            if str(complaint.hostel_id) not in user_hostel_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete this complaint."
                )
        
        await self.session.delete(complaint)
        await self.session.commit()
        
        return True
    
