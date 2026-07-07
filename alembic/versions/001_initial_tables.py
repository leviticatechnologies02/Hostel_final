"""initial_tables

Revision ID: 001
Revises:
Create Date: 2026-07-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── ENUMS ────────────────────────────────────────────────────────────────
    userrole_enum = sa.Enum('super_admin', 'hostel_admin', 'supervisor', 'student', 'visitor', name='userrole')
    otptype_enum = sa.Enum('registration', 'password_reset', name='otptype')
    hosteltype_enum = sa.Enum('boys', 'girls', 'co-living', name='hosteltype')
    hostelstatus_enum = sa.Enum('pending_approval', 'active', 'inactive', 'suspended', 'rejected', name='hostelstatus')
    roomtype_enum = sa.Enum('single', 'double', 'triple', 'dormitory', name='roomtype')
    bedstatus_enum = sa.Enum('available', 'occupied', 'maintenance', 'reserved', name='bedstatus')
    bookingmode_enum = sa.Enum('daily', 'monthly', name='bookingmode')
    bookingstatus_enum = sa.Enum(
        'draft', 'payment_pending', 'pending_approval', 'approved',
        'rejected', 'checked_in', 'checked_out', 'completed', 'cancelled',
        name='bookingstatus'
    )
    bedstaystatus_enum = sa.Enum('reserved', 'active', 'completed', 'cancelled', name='bedstaystatus')
    waitliststatus_enum = sa.Enum('active', 'notified', 'converted', 'cancelled', name='waitliststatus')
    studentstatus_enum = sa.Enum('active', 'checked_out', 'on_leave', name='studentstatus')
    planstatus_enum = sa.Enum('active', 'inactive', name='planstatus')
    durationtype_enum = sa.Enum('monthly', 'quarterly', 'yearly', 'custom', name='durationtype')

    # ─── USERS ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', userrole_enum, nullable=False),
        sa.Column('profile_picture_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_phone_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])

    # ─── REFRESH TOKENS ───────────────────────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(64), nullable=True),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)

    # ─── OTP VERIFICATIONS ────────────────────────────────────────────────────
    op.create_table(
        'otp_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('otp_code_hash', sa.String(255), nullable=False),
        sa.Column('otp_type', otptype_enum, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_otp_verifications_user_id', 'otp_verifications', ['user_id'])

    # ─── HOSTELS ──────────────────────────────────────────────────────────────
    op.create_table(
        'hostels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('hostel_type', hosteltype_enum, nullable=False),
        sa.Column('status', hostelstatus_enum, nullable=False, server_default='pending_approval'),
        sa.Column('address_line1', sa.String(255), nullable=False),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(120), nullable=False),
        sa.Column('state', sa.String(120), nullable=False),
        sa.Column('country', sa.String(120), nullable=False, server_default='India'),
        sa.Column('pincode', sa.String(20), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('rules_and_regulations', sa.Text(), nullable=True),
    )
    op.create_index('ix_hostels_name', 'hostels', ['name'])
    op.create_index('ix_hostels_slug', 'hostels', ['slug'], unique=True)
    op.create_index('ix_hostels_hostel_type', 'hostels', ['hostel_type'])
    op.create_index('ix_hostels_city', 'hostels', ['city'])
    op.create_index('ix_hostels_state', 'hostels', ['state'])

    # ─── HOSTEL AMENITIES ─────────────────────────────────────────────────────
    op.create_table(
        'hostel_amenities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
    )
    op.create_index('ix_hostel_amenities_hostel_id', 'hostel_amenities', ['hostel_id'])

    # ─── HOSTEL IMAGES ────────────────────────────────────────────────────────
    op.create_table(
        'hostel_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=False),
        sa.Column('caption', sa.String(255), nullable=True),
        sa.Column('image_type', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_hostel_images_hostel_id', 'hostel_images', ['hostel_id'])

    # ─── ADMIN HOSTEL MAPPINGS ────────────────────────────────────────────────
    op.create_table(
        'admin_hostel_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.UniqueConstraint('admin_id', 'hostel_id', name='uq_admin_hostel'),
    )
    op.create_index('ix_admin_hostel_mappings_admin_id', 'admin_hostel_mappings', ['admin_id'])
    op.create_index('ix_admin_hostel_mappings_hostel_id', 'admin_hostel_mappings', ['hostel_id'])

    # ─── SUPERVISOR HOSTEL MAPPINGS ───────────────────────────────────────────
    op.create_table(
        'supervisor_hostel_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('supervisor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.UniqueConstraint('supervisor_id', 'hostel_id', name='uq_supervisor_hostel'),
    )
    op.create_index('ix_supervisor_hostel_mappings_supervisor_id', 'supervisor_hostel_mappings', ['supervisor_id'])
    op.create_index('ix_supervisor_hostel_mappings_hostel_id', 'supervisor_hostel_mappings', ['hostel_id'])

    # ─── VISITOR FAVORITES ────────────────────────────────────────────────────
    op.create_table(
        'visitor_favorites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('visitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('visitor_id', 'hostel_id', name='uq_visitor_favorite'),
    )
    op.create_index('ix_visitor_favorites_visitor_id', 'visitor_favorites', ['visitor_id'])
    op.create_index('ix_visitor_favorites_hostel_id', 'visitor_favorites', ['hostel_id'])

    # ─── ROOMS ────────────────────────────────────────────────────────────────
    op.create_table(
        'rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_number', sa.String(50), nullable=False),
        sa.Column('floor', sa.Integer(), nullable=False),
        sa.Column('room_type', roomtype_enum, nullable=False),
        sa.Column('total_beds', sa.Integer(), nullable=False),
        sa.Column('daily_rent', sa.Numeric(10, 2), nullable=False),
        sa.Column('monthly_rent', sa.Numeric(10, 2), nullable=False),
        sa.Column('security_deposit', sa.Numeric(10, 2), nullable=False),
        sa.Column('dimensions', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint('hostel_id', 'room_number', name='uq_room_hostel_number'),
    )
    op.create_index('ix_rooms_hostel_id', 'rooms', ['hostel_id'])
    op.create_index('ix_rooms_room_type', 'rooms', ['room_type'])

    # ─── BEDS ─────────────────────────────────────────────────────────────────
    op.create_table(
        'beds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bed_number', sa.String(50), nullable=False),
        sa.Column('status', bedstatus_enum, nullable=False, server_default='available'),
        sa.UniqueConstraint('room_id', 'bed_number', name='uq_bed_room_number'),
    )
    op.create_index('ix_beds_hostel_id', 'beds', ['hostel_id'])
    op.create_index('ix_beds_room_id', 'beds', ['room_id'])

    # ─── PLANS ────────────────────────────────────────────────────────────────
    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('price_yearly', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('duration_type', durationtype_enum, nullable=False, server_default='monthly'),
        sa.Column('duration_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('hostel_limit', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('admin_limit', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('auto_renew_allowed', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('status', planstatus_enum, nullable=False, server_default='active'),
    )
    op.create_index('ix_plans_name', 'plans', ['name'])
    op.create_index('ix_plans_code', 'plans', ['code'], unique=True)

    # ─── PLAN FEATURES ────────────────────────────────────────────────────────
    op.create_table(
        'plan_features',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature_name', sa.String(100), nullable=False),
        sa.Column('feature_value', sa.String(255), nullable=True),
        sa.Column('is_included', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_plan_features_plan_id', 'plan_features', ['plan_id'])

    # ─── BOOKINGS ─────────────────────────────────────────────────────────────
    op.create_table(
        'bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('booking_number', sa.String(50), nullable=False),
        sa.Column('visitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('beds.id'), nullable=True),
        sa.Column('booking_mode', bookingmode_enum, nullable=False),
        sa.Column('status', bookingstatus_enum, nullable=False),
        sa.Column('check_in_date', sa.Date(), nullable=False),
        sa.Column('check_out_date', sa.Date(), nullable=False),
        sa.Column('total_nights', sa.Integer(), nullable=True),
        sa.Column('total_months', sa.Integer(), nullable=True),
        sa.Column('base_rent_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('security_deposit', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('booking_advance', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('grand_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(50), nullable=True),
        sa.Column('occupation', sa.String(255), nullable=True),
        sa.Column('institution', sa.String(255), nullable=True),
        sa.Column('current_address', sa.Text(), nullable=True),
        sa.Column('id_type', sa.String(100), nullable=True),
        sa.Column('id_document_url', sa.String(500), nullable=True),
        sa.Column('emergency_contact_name', sa.String(255), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(30), nullable=True),
        sa.Column('emergency_contact_relationship', sa.String(100), nullable=True),
        sa.Column('guardian_name', sa.String(255), nullable=True),
        sa.Column('guardian_phone', sa.String(30), nullable=True),
        sa.Column('special_requirements', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.CheckConstraint('check_out_date > check_in_date', name='ck_booking_dates'),
    )
    op.create_index('ix_bookings_booking_number', 'bookings', ['booking_number'], unique=True)
    op.create_index('ix_bookings_visitor_id', 'bookings', ['visitor_id'])
    op.create_index('ix_bookings_hostel_id', 'bookings', ['hostel_id'])
    op.create_index('ix_bookings_room_id', 'bookings', ['room_id'])
    op.create_index('ix_bookings_bed_id', 'bookings', ['bed_id'])
    op.create_index('ix_bookings_booking_mode', 'bookings', ['booking_mode'])
    op.create_index('ix_bookings_status', 'bookings', ['status'])

    # ─── BOOKING STATUS HISTORY ───────────────────────────────────────────────
    op.create_table(
        'booking_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_status', bookingstatus_enum, nullable=True),
        sa.Column('new_status', bookingstatus_enum, nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
    )
    op.create_index('ix_booking_status_history_booking_id', 'booking_status_history', ['booking_id'])

    # ─── STUDENTS ─────────────────────────────────────────────────────────────
    op.create_table(
        'students',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('beds.id'), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('student_number', sa.String(50), nullable=False),
        sa.Column('check_in_date', sa.Date(), nullable=False),
        sa.Column('check_out_date', sa.Date(), nullable=True),
        sa.Column('status', studentstatus_enum, nullable=False, server_default='active'),
    )
    op.create_index('ix_students_user_id', 'students', ['user_id'])
    op.create_index('ix_students_hostel_id', 'students', ['hostel_id'])
    op.create_index('ix_students_room_id', 'students', ['room_id'])
    op.create_index('ix_students_bed_id', 'students', ['bed_id'])
    op.create_index('ix_students_student_number', 'students', ['student_number'], unique=True)
    op.create_unique_constraint('uq_students_booking_id', 'students', ['booking_id'])

    # ─── BED STAYS ────────────────────────────────────────────────────────────
    op.create_table(
        'bed_stays',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('beds.id', ondelete='CASCADE'), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', bedstaystatus_enum, nullable=False),
        sa.CheckConstraint('end_date > start_date', name='ck_bed_stay_dates'),
    )
    op.create_index('ix_bed_stays_hostel_id', 'bed_stays', ['hostel_id'])
    op.create_index('ix_bed_stays_bed_id', 'bed_stays', ['bed_id'])
    op.create_index('ix_bed_stays_booking_id', 'bed_stays', ['booking_id'])
    op.create_index('ix_bed_stays_student_id', 'bed_stays', ['student_id'])
    op.create_index('ix_bed_stays_status', 'bed_stays', ['status'])

    # ─── INQUIRIES ────────────────────────────────────────────────────────────
    op.create_table(
        'inquiries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
    )
    op.create_index('ix_inquiries_hostel_id', 'inquiries', ['hostel_id'])

    # ─── WAITLIST ENTRIES ─────────────────────────────────────────────────────
    op.create_table(
        'waitlist_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('visitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('beds.id'), nullable=True),
        sa.Column('check_in_date', sa.Date(), nullable=False),
        sa.Column('check_out_date', sa.Date(), nullable=False),
        sa.Column('booking_mode', bookingmode_enum, nullable=False),
        sa.Column('status', waitliststatus_enum, nullable=False, server_default='active'),
        sa.Column('notified_at', sa.Date(), nullable=True),
    )
    op.create_index('ix_waitlist_entries_visitor_id', 'waitlist_entries', ['visitor_id'])
    op.create_index('ix_waitlist_entries_hostel_id', 'waitlist_entries', ['hostel_id'])
    op.create_index('ix_waitlist_entries_room_id', 'waitlist_entries', ['room_id'])
    op.create_index('ix_waitlist_entries_bed_id', 'waitlist_entries', ['bed_id'])
    op.create_index('ix_waitlist_entries_booking_mode', 'waitlist_entries', ['booking_mode'])
    op.create_index('ix_waitlist_entries_status', 'waitlist_entries', ['status'])

    # ─── PAYMENTS ─────────────────────────────────────────────────────────────
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=True),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('payment_type', sa.String(50), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('gateway_order_id', sa.String(120), nullable=True),
        sa.Column('gateway_payment_id', sa.String(120), nullable=True),
        sa.Column('gateway_signature', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.Column('failure_code', sa.String(50), nullable=True),
        sa.CheckConstraint(
            'booking_id IS NOT NULL OR student_id IS NOT NULL',
            name='ck_payment_has_context',
        ),
    )
    op.create_index('ix_payments_hostel_id', 'payments', ['hostel_id'])
    op.create_index('ix_payments_student_id', 'payments', ['student_id'])
    op.create_index('ix_payments_booking_id', 'payments', ['booking_id'])
    op.create_index('ix_payments_gateway_order_id', 'payments', ['gateway_order_id'])

    # ─── PAYMENT WEBHOOK EVENTS ───────────────────────────────────────────────
    op.create_table(
        'payment_webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
    )

    # ─── COMPLAINTS ───────────────────────────────────────────────────────────
    op.create_table(
        'complaints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('complaint_number', sa.String(50), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_complaints_complaint_number', 'complaints', ['complaint_number'], unique=True)
    op.create_index('ix_complaints_student_id', 'complaints', ['student_id'])
    op.create_index('ix_complaints_hostel_id', 'complaints', ['hostel_id'])

    # ─── COMPLAINT COMMENTS ───────────────────────────────────────────────────
    op.create_table(
        'complaint_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('complaint_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
    )
    op.create_index('ix_complaint_comments_complaint_id', 'complaint_comments', ['complaint_id'])
    op.create_index('ix_complaint_comments_author_id', 'complaint_comments', ['author_id'])

    # ─── ATTENDANCE RECORDS ───────────────────────────────────────────────────
    op.create_table(
        'attendance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('check_in_time', sa.Time(), nullable=True),
        sa.Column('check_out_time', sa.Time(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('marked_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('remarks', sa.String(255), nullable=True),
        sa.UniqueConstraint('student_id', 'date', name='uq_attendance_student_date'),
    )
    op.create_index('ix_attendance_records_student_id', 'attendance_records', ['student_id'])
    op.create_index('ix_attendance_records_hostel_id', 'attendance_records', ['hostel_id'])
    op.create_index('ix_attendance_records_date', 'attendance_records', ['date'])

    # ─── MAINTENANCE REQUESTS ─────────────────────────────────────────────────
    op.create_table(
        'maintenance_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=True),
        sa.Column('reported_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('estimated_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('actual_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('assigned_vendor_name', sa.String(255), nullable=True),
        sa.Column('vendor_contact', sa.String(50), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requires_admin_approval', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_maintenance_requests_hostel_id', 'maintenance_requests', ['hostel_id'])

    # ─── NOTICES ──────────────────────────────────────────────────────────────
    op.create_table(
        'notices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('notice_type', sa.String(100), nullable=False),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('publish_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
    )
    op.create_index('ix_notices_hostel_id', 'notices', ['hostel_id'])

    # ─── NOTICE READS ─────────────────────────────────────────────────────────
    op.create_table(
        'notice_reads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('notices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('notice_id', 'user_id', name='uq_notice_read_notice_user'),
    )
    op.create_index('ix_notice_reads_notice_id', 'notice_reads', ['notice_id'])
    op.create_index('ix_notice_reads_user_id', 'notice_reads', ['user_id'])

    # ─── MESS MENUS ───────────────────────────────────────────────────────────
    op.create_table(
        'mess_menus',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
    )
    op.create_index('ix_mess_menus_hostel_id', 'mess_menus', ['hostel_id'])
    op.create_index('ix_mess_menus_week_start_date', 'mess_menus', ['week_start_date'])

    # ─── MESS MENU ITEMS ──────────────────────────────────────────────────────
    op.create_table(
        'mess_menu_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('menu_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('mess_menus.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day_of_week', sa.String(20), nullable=False),
        sa.Column('meal_type', sa.String(50), nullable=False),
        sa.Column('item_name', sa.String(255), nullable=False),
        sa.Column('is_veg', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('special_note', sa.String(255), nullable=True),
    )
    op.create_index('ix_mess_menu_items_menu_id', 'mess_menu_items', ['menu_id'])

    # ─── SUBSCRIPTIONS ────────────────────────────────────────────────────────
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=True),
        sa.Column('tier', sa.String(50), nullable=False),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_subscriptions_hostel_id', 'subscriptions', ['hostel_id'])
    op.create_index('ix_subscriptions_plan_id', 'subscriptions', ['plan_id'])

    # ─── REVIEWS ──────────────────────────────────────────────────────────────
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('visitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hostels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('overall_rating', sa.Float(), nullable=False),
        sa.Column('cleanliness_rating', sa.Float(), nullable=False),
        sa.Column('food_rating', sa.Float(), nullable=False),
        sa.Column('security_rating', sa.Float(), nullable=False),
        sa.Column('value_rating', sa.Float(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('admin_reply', sa.Text(), nullable=True),
    )
    op.create_index('ix_reviews_visitor_id', 'reviews', ['visitor_id'])
    op.create_index('ix_reviews_hostel_id', 'reviews', ['hostel_id'])


def downgrade() -> None:
    # Drop in reverse order of creation (children before parents)
    op.drop_table('reviews')
    op.drop_table('subscriptions')
    op.drop_table('mess_menu_items')
    op.drop_table('mess_menus')
    op.drop_table('notice_reads')
    op.drop_table('notices')
    op.drop_table('maintenance_requests')
    op.drop_table('attendance_records')
    op.drop_table('complaint_comments')
    op.drop_table('complaints')
    op.drop_table('payment_webhook_events')
    op.drop_table('payments')
    op.drop_table('bed_stays')
    op.drop_table('waitlist_entries')
    op.drop_table('inquiries')
    op.drop_table('students')
    op.drop_table('booking_status_history')
    op.drop_table('bookings')
    op.drop_table('plan_features')
    op.drop_table('plans')
    op.drop_table('beds')
    op.drop_table('rooms')
    op.drop_table('visitor_favorites')
    op.drop_table('supervisor_hostel_mappings')
    op.drop_table('admin_hostel_mappings')
    op.drop_table('hostel_images')
    op.drop_table('hostel_amenities')
    op.drop_table('hostels')
    op.drop_table('otp_verifications')
    op.drop_table('refresh_tokens')
    op.drop_table('users')

    # Drop enums
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='otptype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='hosteltype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='hostelstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='roomtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='bedstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='bookingmode').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='bookingstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='bedstaystatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='waitliststatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='studentstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='planstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='durationtype').drop(op.get_bind(), checkfirst=True)
