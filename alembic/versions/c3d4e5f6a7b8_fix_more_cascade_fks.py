"""fix_more_cascade_fks

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-16 11:14:00.000000

Fix missing ON DELETE CASCADE on:
- bed_stays.booking_id -> bookings.id
- bed_stays.student_id -> students.id
- waitlist_entries.room_id -> rooms.id
- waitlist_entries.bed_id -> beds.id
- maintenance_requests.room_id -> rooms.id
- notices.hostel_id -> hostels.id
- reviews.booking_id -> bookings.id
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ON DELETE CASCADE to bed_stays, waitlist_entries, maintenance_requests, notices, reviews."""

    # bed_stays
    op.drop_constraint('bed_stays_booking_id_fkey', 'bed_stays', type_='foreignkey')
    op.drop_constraint('bed_stays_student_id_fkey', 'bed_stays', type_='foreignkey')
    op.create_foreign_key(
        'bed_stays_booking_id_fkey', 'bed_stays', 'bookings',
        ['booking_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'bed_stays_student_id_fkey', 'bed_stays', 'students',
        ['student_id'], ['id'], ondelete='CASCADE'
    )

    # waitlist_entries
    op.drop_constraint('waitlist_entries_room_id_fkey', 'waitlist_entries', type_='foreignkey')
    op.drop_constraint('waitlist_entries_bed_id_fkey', 'waitlist_entries', type_='foreignkey')
    op.create_foreign_key(
        'waitlist_entries_room_id_fkey', 'waitlist_entries', 'rooms',
        ['room_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'waitlist_entries_bed_id_fkey', 'waitlist_entries', 'beds',
        ['bed_id'], ['id'], ondelete='CASCADE'
    )

    # maintenance_requests
    op.drop_constraint('maintenance_requests_room_id_fkey', 'maintenance_requests', type_='foreignkey')
    op.create_foreign_key(
        'maintenance_requests_room_id_fkey', 'maintenance_requests', 'rooms',
        ['room_id'], ['id'], ondelete='CASCADE'
    )

    # notices
    op.drop_constraint('notices_hostel_id_fkey', 'notices', type_='foreignkey')
    op.create_foreign_key(
        'notices_hostel_id_fkey', 'notices', 'hostels',
        ['hostel_id'], ['id'], ondelete='CASCADE'
    )

    # reviews
    op.drop_constraint('reviews_booking_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key(
        'reviews_booking_id_fkey', 'reviews', 'bookings',
        ['booking_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    """Revert CASCADE back to default (RESTRICT)."""

    # reviews
    op.drop_constraint('reviews_booking_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_booking_id_fkey', 'reviews', 'bookings', ['booking_id'], ['id'])

    # notices
    op.drop_constraint('notices_hostel_id_fkey', 'notices', type_='foreignkey')
    op.create_foreign_key('notices_hostel_id_fkey', 'notices', 'hostels', ['hostel_id'], ['id'])

    # maintenance_requests
    op.drop_constraint('maintenance_requests_room_id_fkey', 'maintenance_requests', type_='foreignkey')
    op.create_foreign_key('maintenance_requests_room_id_fkey', 'maintenance_requests', 'rooms', ['room_id'], ['id'])

    # waitlist_entries
    op.drop_constraint('waitlist_entries_room_id_fkey', 'waitlist_entries', type_='foreignkey')
    op.drop_constraint('waitlist_entries_bed_id_fkey', 'waitlist_entries', type_='foreignkey')
    op.create_foreign_key('waitlist_entries_room_id_fkey', 'waitlist_entries', 'rooms', ['room_id'], ['id'])
    op.create_foreign_key('waitlist_entries_bed_id_fkey', 'waitlist_entries', 'beds', ['bed_id'], ['id'])

    # bed_stays
    op.drop_constraint('bed_stays_booking_id_fkey', 'bed_stays', type_='foreignkey')
    op.drop_constraint('bed_stays_student_id_fkey', 'bed_stays', type_='foreignkey')
    op.create_foreign_key('bed_stays_booking_id_fkey', 'bed_stays', 'bookings', ['booking_id'], ['id'])
    op.create_foreign_key('bed_stays_student_id_fkey', 'bed_stays', 'students', ['student_id'], ['id'])
