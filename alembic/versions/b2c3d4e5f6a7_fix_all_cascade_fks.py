"""fix_all_cascade_fks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-16 11:00:00.000000

Fix missing ON DELETE CASCADE on:
- payments.student_id  -> students.id
- payments.booking_id  -> bookings.id
- students.room_id     -> rooms.id
- students.bed_id      -> beds.id
- students.booking_id  -> bookings.id
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ON DELETE CASCADE to all missing FK constraints."""

    # ── payments table ────────────────────────────────────────────────────────
    op.drop_constraint('payments_student_id_fkey', 'payments', type_='foreignkey')
    op.drop_constraint('payments_booking_id_fkey', 'payments', type_='foreignkey')

    op.create_foreign_key(
        'payments_student_id_fkey', 'payments', 'students',
        ['student_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'payments_booking_id_fkey', 'payments', 'bookings',
        ['booking_id'], ['id'], ondelete='CASCADE'
    )

    # ── students table ────────────────────────────────────────────────────────
    op.drop_constraint('students_room_id_fkey', 'students', type_='foreignkey')
    op.drop_constraint('students_bed_id_fkey', 'students', type_='foreignkey')
    op.drop_constraint('students_booking_id_fkey', 'students', type_='foreignkey')

    op.create_foreign_key(
        'students_room_id_fkey', 'students', 'rooms',
        ['room_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'students_bed_id_fkey', 'students', 'beds',
        ['bed_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'students_booking_id_fkey', 'students', 'bookings',
        ['booking_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    """Revert CASCADE back to default (RESTRICT)."""

    # payments
    op.drop_constraint('payments_student_id_fkey', 'payments', type_='foreignkey')
    op.drop_constraint('payments_booking_id_fkey', 'payments', type_='foreignkey')
    op.create_foreign_key('payments_student_id_fkey', 'payments', 'students', ['student_id'], ['id'])
    op.create_foreign_key('payments_booking_id_fkey', 'payments', 'bookings', ['booking_id'], ['id'])

    # students
    op.drop_constraint('students_room_id_fkey', 'students', type_='foreignkey')
    op.drop_constraint('students_bed_id_fkey', 'students', type_='foreignkey')
    op.drop_constraint('students_booking_id_fkey', 'students', type_='foreignkey')
    op.create_foreign_key('students_room_id_fkey', 'students', 'rooms', ['room_id'], ['id'])
    op.create_foreign_key('students_bed_id_fkey', 'students', 'beds', ['bed_id'], ['id'])
    op.create_foreign_key('students_booking_id_fkey', 'students', 'bookings', ['booking_id'], ['id'])
