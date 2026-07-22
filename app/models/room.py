from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import BedStay
    from app.models.hostel import Hostel


class RoomType(str, enum.Enum):
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    QUADRUPLE = "quadruple"
    DORMITORY = "dormitory"


class BedStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"


class Room(BaseModel):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("hostel_id", "room_number", name="uq_room_hostel_number"),
    )

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    room_number: Mapped[str] = mapped_column(String(50))
    floor: Mapped[int]
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType), index=True)
    total_beds: Mapped[int]
    daily_rent: Mapped[float] = mapped_column(Numeric(10, 2))
    monthly_rent: Mapped[float] = mapped_column(Numeric(10, 2))
    security_deposit: Mapped[float] = mapped_column(Numeric(10, 2))
    dimensions: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    hostel: Mapped[Hostel] = relationship("Hostel", back_populates="rooms")
    beds: Mapped[list[Bed]] = relationship(
        "Bed", back_populates="room", cascade="all, delete-orphan"
    )


class Bed(BaseModel):
    __tablename__ = "beds"
    __table_args__ = (
        UniqueConstraint("room_id", "bed_number", name="uq_bed_room_number"),
    )

    hostel_id: Mapped[str] = mapped_column(
        ForeignKey("hostels.id", ondelete="CASCADE"), index=True
    )
    room_id: Mapped[str] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    bed_number: Mapped[str] = mapped_column(String(50))
    status: Mapped[BedStatus] = mapped_column(Enum(BedStatus), default=BedStatus.AVAILABLE)

    room: Mapped[Room] = relationship("Room", back_populates="beds")
    bed_stays: Mapped[list[BedStay]] = relationship(
        "BedStay", back_populates="bed", cascade="all, delete-orphan"
    )
