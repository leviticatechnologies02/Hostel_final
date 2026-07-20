from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import TimestampedResponse


class ComplaintCreateRequest(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    priority: str = Field(min_length=2, max_length=50)
    photo_url: str | None = Field(default=None, max_length=500)


class ComplaintUpdateRequest(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    resolution_notes: str | None = None


class ComplaintResponse(TimestampedResponse):
    complaint_number: str
    student_id: str
    student_name: str | None = None
    hostel_id: str
    category: str
    title: str
    description: str
    priority: str
    status: str
    assigned_to: str | None = None
    photo_url: str | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    sla_deadline: datetime
    sla_breached: bool
