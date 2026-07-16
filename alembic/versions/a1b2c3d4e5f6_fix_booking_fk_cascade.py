"""fix_booking_fk_cascade

Revision ID: a1b2c3d4e5f6
Revises: 74d1eaf47673
Create Date: 2026-07-16 10:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '74d1eaf47673'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix foreign key constraints on bookings.room_id and bookings.bed_id to CASCADE on delete."""

    # Drop existing FK constraints
    op.drop_constraint('bookings_room_id_fkey', 'bookings', type_='foreignkey')
    op.drop_constraint('bookings_bed_id_fkey', 'bookings', type_='foreignkey')

    # Re-create with ON DELETE CASCADE
    op.create_foreign_key(
        'bookings_room_id_fkey',
        'bookings', 'rooms',
        ['room_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'bookings_bed_id_fkey',
        'bookings', 'beds',
        ['bed_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Revert CASCADE to restrict (default)."""

    op.drop_constraint('bookings_room_id_fkey', 'bookings', type_='foreignkey')
    op.drop_constraint('bookings_bed_id_fkey', 'bookings', type_='foreignkey')

    op.create_foreign_key(
        'bookings_room_id_fkey',
        'bookings', 'rooms',
        ['room_id'], ['id']
    )
    op.create_foreign_key(
        'bookings_bed_id_fkey',
        'bookings', 'beds',
        ['bed_id'], ['id']
    )
