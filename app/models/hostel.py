from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.room import Room
    from app.models.user import User


class HostelType(str, enum.Enum):
    BOYS = "boys"
    GIRLS = "girls"
    COED = "co-living"


class HostelStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class Hostel(BaseModel):
    __tablename__ = "hostels"

    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    hostel_type: Mapped[HostelType] = mapped_column(Enum(HostelType), index=True)
    status: Mapped[HostelStatus] = mapped_column(
        Enum(HostelStatus), default=HostelStatus.PENDING_APPROVAL
    )
    address_line1: Mapped[str] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(120), index=True)
    country: Mapped[str] = mapped_column(String(120), default="India")
    pincode: Mapped[str] = mapped_column(String(20))
    latitude: Mapped[float]
    longitude: Mapped[float]
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rules_and_regulations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    amenities: Mapped[list[HostelAmenity]] = relationship(
        "HostelAmenity", back_populates="hostel", cascade="all, delete-orphan"
    )
    images: Mapped[list[HostelImage]] = relationship(
        "HostelImage",
        back_populates="hostel",
        cascade="all, delete-orphan",
        order_by="HostelImage.sort_order",
    )
    admin_mappings: Mapped[list[AdminHostelMapping]] = relationship(
        "AdminHostelMapping", back_populates="hostel", cascade="all, delete-orphan"
    )
    supervisor_mappings: Mapped[list[SupervisorHostelMapping]] = relationship(
        "SupervisorHostelMapping", back_populates="hostel", cascade="all, delete-orphan"
    )
    rooms: Mapped[list[Room]] = relationship(
        "Room", back_populates="hostel", cascade="all, delete-orphan"
    )


class HostelAmenity(BaseModel):
    __tablename__ = "hostel_amenities"

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(150))

    hostel: Mapped[Hostel] = relationship("Hostel", back_populates="amenities")


class HostelImage(BaseModel):
    __tablename__ = "hostel_images"

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_type: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    hostel: Mapped[Hostel] = relationship("Hostel", back_populates="images")


class AdminHostelMapping(BaseModel):
    __tablename__ = "admin_hostel_mappings"
    __table_args__ = (
        UniqueConstraint("admin_id", "hostel_id", name="uq_admin_hostel"),
    )

    admin_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    admin: Mapped[User] = relationship(
        "User", back_populates="admin_hostel_mappings", foreign_keys=[admin_id]
    )
    hostel: Mapped[Hostel] = relationship("Hostel", back_populates="admin_mappings")


class SupervisorHostelMapping(BaseModel):
    __tablename__ = "supervisor_hostel_mappings"
    __table_args__ = (
        UniqueConstraint("supervisor_id", "hostel_id", name="uq_supervisor_hostel"),
    )

    supervisor_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    supervisor: Mapped[User] = relationship(
        "User",
        back_populates="supervisor_hostel_mappings",
        foreign_keys=[supervisor_id],
    )
    hostel: Mapped[Hostel] = relationship("Hostel", back_populates="supervisor_mappings")


class VisitorFavorite(BaseModel):
    """Visitor saved/favorite hostels."""
    __tablename__ = "visitor_favorites"
    __table_args__ = (
        UniqueConstraint("visitor_id", "hostel_id", name="uq_visitor_favorite"),
    )

    visitor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    hostel_id: Mapped[str] = mapped_column(ForeignKey("hostels.id", ondelete="CASCADE"), index=True)
