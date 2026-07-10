"""
app/api/v1/uploads/routes.py

Centralized file upload endpoints — fully Swagger-testable with "Choose File" button.
Uses FastAPI UploadFile (multipart/form-data). All files go directly to Cloudinary.
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.responses import Response

from app.dependencies import DBSession, CurrentUser, require_roles
from app.integrations.cloudinary_client import get_cloudinary_client

router = APIRouter()

# ── Role aliases ────────────────────────────────────────────────────────────
AnyAuthUser    = Annotated[CurrentUser, Depends(require_roles("visitor", "student", "hostel_admin", "supervisor", "super_admin"))]
AdminUser      = Annotated[CurrentUser, Depends(require_roles("hostel_admin", "super_admin"))]
StudentUser    = Annotated[CurrentUser, Depends(require_roles("student"))]
VisitorUser    = Annotated[CurrentUser, Depends(require_roles("visitor"))]
SupervisorUser = Annotated[CurrentUser, Depends(require_roles("supervisor", "hostel_admin", "super_admin"))]

# ── Allowed MIME types ───────────────────────────────────────────────────────
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_DOC_TYPES   = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
_MAX_IMG_MB  = 5
_MAX_DOC_MB  = 10


def _validate(content: bytes, ct: str, allowed: set, max_mb: int, label: str) -> None:
    """Raise HTTPException 400 for bad file type or oversized file."""
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(400, f"{label} exceeds {max_mb} MB limit.")
    if ct.lower() not in allowed:
        raise HTTPException(
            400,
            f"Unsupported file type '{ct}'. Allowed: {', '.join(sorted(allowed))}."
        )


def _unique_name(user_id: str, filename: str | None, folder: str) -> str:
    """Build a collision-free Cloudinary path using a UUID prefix."""
    safe_name = filename or "file"
    return f"{folder}/{user_id}/{uuid.uuid4().hex}_{safe_name}"


async def _cloudinary_upload(file_name: str, content: bytes, ct: str) -> str:
    """Upload to Cloudinary, converting RuntimeError → HTTP 500."""
    try:
        return await get_cloudinary_client().upload(
            file_name=file_name,
            content=content,
            content_type=ct,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ════════════════════════════════════════════════════════════════
# 1. PROFILE PICTURE  — all authenticated users
# ════════════════════════════════════════════════════════════════

@router.post(
    "/profile-picture",
    summary="Upload profile picture",
    tags=["uploads"],
)
async def upload_profile_picture(
    current_user: AnyAuthUser,
    db: DBSession,
    file: UploadFile = File(..., description="Profile picture — JPEG / PNG / WebP (max 5 MB)"),
):
    """
    Upload a profile picture for the currently authenticated user.

    - Accepted types: **JPEG, PNG, WebP**
    - Max size: **5 MB**
    - The image is uploaded to Cloudinary and `profile_picture_url` is automatically
      updated in the users table — no separate PATCH needed.
    """
    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _IMAGE_TYPES, _MAX_IMG_MB, "Profile picture")

    path = _unique_name(current_user.id, file.filename, "profile")
    url  = await _cloudinary_upload(path, content, ct)

    from sqlalchemy import update as sa_update
    from app.models.user import User
    await db.execute(
        sa_update(User)
        .where(User.id == current_user.id)
        .values(profile_picture_url=url)
    )
    await db.commit()
    return {"url": url, "filename": file.filename, "status": "success"}


# ════════════════════════════════════════════════════════════════
# 2. HOSTEL REGISTRATION DOCUMENT — public (no auth required)
# ════════════════════════════════════════════════════════════════

@router.post(
    "/hostel-registration-document",
    summary="Upload hostel registration document",
    tags=["uploads"],
)
async def upload_hostel_registration_document(
    file: UploadFile = File(..., description="Business registration doc — JPEG / PNG / PDF (max 10 MB)"),
):
    """
    Upload a document (like trade license, GST certificate) for hostel registration.

    - Accepted types: **JPEG, PNG, WebP, PDF**
    - Max size: **10 MB**
    - Returns a `url` which you should pass as `document_url` when calling `POST /api/v1/public/hostels/register`.
    - This endpoint is fully public (no auth required).
    """
    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _DOC_TYPES, _MAX_DOC_MB, "Registration document")

    # Use a generic public prefix since the user isn't logged in
    path = _unique_name("public_registration", file.filename, "registration-docs")
    url  = await _cloudinary_upload(path, content, ct)

    return {"url": url, "filename": file.filename, "status": "success"}


# ════════════════════════════════════════════════════════════════
# 3. ID DOCUMENT  — visitor / student / any auth user
# ════════════════════════════════════════════════════════════════

@router.post(
    "/id-document",
    summary="Upload ID document",
    tags=["uploads"],
)
async def upload_id_document(
    current_user: AnyAuthUser,
    file: UploadFile = File(..., description="ID proof — JPEG / PNG / WebP / PDF (max 10 MB)"),
):
    """
    Upload an ID document (Aadhaar, Passport, Driving Licence, etc.).

    - Accepted types: **JPEG, PNG, WebP, PDF**
    - Max size: **10 MB**
    - Returns `url` — store it via `PATCH /api/v1/bookings/{booking_id}/applicant`
      or wherever the frontend needs the ID document URL.
    """
    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _DOC_TYPES, _MAX_DOC_MB, "ID document")

    path = _unique_name(current_user.id, file.filename, "id-docs")
    url  = await _cloudinary_upload(path, content, ct)
    return {"url": url, "filename": file.filename, "content_type": ct, "status": "success"}


# ════════════════════════════════════════════════════════════════
# 3. COMPLAINT ATTACHMENT  — any authenticated user
# ════════════════════════════════════════════════════════════════

@router.post(
    "/complaint-attachment",
    summary="Upload complaint attachment",
    tags=["uploads"],
)
async def upload_complaint_attachment(
    current_user: AnyAuthUser,
    file: UploadFile = File(..., description="Complaint attachment — JPEG / PNG / WebP / PDF (max 10 MB)"),
):
    """
    Upload a photo or PDF to attach to a complaint.

    - Accepted types: **JPEG, PNG, WebP, PDF**
    - Max size: **10 MB**
    - Returns `url` — pass it as `attachment_url` when creating the complaint.
    """
    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _DOC_TYPES, _MAX_DOC_MB, "Attachment")

    path = _unique_name(current_user.id, file.filename, "complaints")
    url  = await _cloudinary_upload(path, content, ct)
    return {"url": url, "filename": file.filename, "content_type": ct, "status": "success"}


# ════════════════════════════════════════════════════════════════
# 4. BOOKING ID DOCUMENT  — visitor uploads doc linked to booking
# ════════════════════════════════════════════════════════════════

@router.post(
    "/booking-document/{booking_id}",
    summary="Upload booking ID document",
    tags=["uploads"],
)
async def upload_booking_document(
    booking_id: str,
    current_user: AnyAuthUser,
    db: DBSession,
    file: UploadFile = File(..., description="ID document — JPEG / PNG / WebP / PDF (max 10 MB)"),
    id_type: str = Form(None, description="Document type: 'Aadhaar', 'Passport', 'Driving Licence', 'Voter ID', 'PAN Card', etc."),
):
    """
    **Upload an ID document for a specific booking.**

    - Uploads the file to Cloudinary and saves the URL directly to the booking record.
    - After upload, the **Documents column** in the admin Bookings page will show a view link.
    - Accepted types: **JPEG, PNG, WebP, PDF**
    - Max size: **10 MB**

    **Flow:**
    1. Visitor uploads their Aadhaar / Passport using this endpoint.
    2. Admin sees a 📄 icon in the Documents column of the Bookings page.
    3. Admin clicks → `GET /api/v1/admin/bookings/{booking_id}/document` → views the doc.
    """
    from sqlalchemy import select, update as sa_update
    from app.models.booking import Booking

    # Verify booking exists
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Booking not found.")

    # Only the booking owner or admin can upload
    is_admin = current_user.role in ("hostel_admin", "super_admin", "supervisor")
    is_owner = str(booking.visitor_id) == str(current_user.id)
    if not is_admin and not is_owner:
        raise HTTPException(403, "You can only upload documents for your own booking.")

    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _DOC_TYPES, _MAX_DOC_MB, "ID document")

    path = _unique_name(booking_id, file.filename, "booking-docs")
    url  = await _cloudinary_upload(path, content, ct)

    # Save URL and id_type directly to the booking record
    await db.execute(
        sa_update(Booking)
        .where(Booking.id == booking_id)
        .values(id_document_url=url, id_type=id_type)
    )
    await db.commit()

    return {
        "booking_id":      booking_id,
        "booking_number":  booking.booking_number,
        "id_type":         id_type,
        "id_document_url": url,
        "filename":        file.filename,
        "has_document":    True,
        "status":          "success",
    }


# ════════════════════════════════════════════════════════════════
# 5. HOSTEL IMAGE  — hostel_admin / super_admin
# ════════════════════════════════════════════════════════════════

@router.post(
    "/hostel-image/{hostel_id}",
    summary="Upload hostel image",
    tags=["uploads"],
    status_code=201,
)
async def upload_hostel_image(
    hostel_id: str,
    current_user: AdminUser,
    db: DBSession,
    file: UploadFile = File(..., description="Hostel image — JPEG / PNG / WebP (max 5 MB)"),
    caption:    str  = Form(None,    description="Optional caption for this image"),
    image_type: str  = Form("gallery", description="gallery | exterior | interior | room | amenity"),
    is_primary: bool = Form(False,   description="Set as the primary/cover image"),
):
    """
    Upload an image for a hostel and save the record to the database.

    - Accepted types: **JPEG, PNG, WebP**
    - Max size: **5 MB**
    - The image is stored in Cloudinary and the URL is saved to `hostel_images` table.
    """
    from app.models.hostel import HostelImage
    from sqlalchemy import select, func, update as sa_update

    # Permission check
    if (
        hasattr(current_user, "hostel_ids")
        and hostel_id not in current_user.hostel_ids
        and current_user.role != "super_admin"
    ):
        raise HTTPException(403, "Access denied to this hostel.")

    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _IMAGE_TYPES, _MAX_IMG_MB, "Hostel image")

    path = _unique_name(hostel_id, file.filename, "hostels")
    url  = await _cloudinary_upload(path, content, ct)

    # Determine next sort order
    result = await db.execute(
        select(func.coalesce(func.max(HostelImage.sort_order), -1))
        .where(HostelImage.hostel_id == hostel_id)
    )
    next_sort = (result.scalar() or -1) + 1

    # If setting as primary, clear any existing primary flag
    if is_primary:
        await db.execute(
            sa_update(HostelImage)
            .where(HostelImage.hostel_id == hostel_id)
            .values(is_primary=False)
        )

    img = HostelImage(
        hostel_id=hostel_id,
        url=url,
        thumbnail_url=url,
        caption=caption,
        image_type=image_type,
        sort_order=next_sort,
        is_primary=is_primary,
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)

    return {
        "id":            img.id,
        "url":           img.url,
        "thumbnail_url": img.thumbnail_url,
        "caption":       img.caption,
        "image_type":    img.image_type,
        "sort_order":    img.sort_order,
        "is_primary":    img.is_primary,
        "status":        "success",
    }


# ════════════════════════════════════════════════════════════════
# 6. DELETE HOSTEL IMAGE
# ════════════════════════════════════════════════════════════════

@router.delete(
    "/hostel-image/{hostel_id}/{image_id}",
    summary="Delete hostel image",
    tags=["uploads"],
    status_code=204,
)
async def delete_hostel_image(
    hostel_id: str,
    image_id:  str,
    current_user: AdminUser,
    db: DBSession,
):
    """
    Delete a hostel image from both Cloudinary and the database.
    """
    from app.models.hostel import HostelImage
    from sqlalchemy import select

    if (
        hasattr(current_user, "hostel_ids")
        and hostel_id not in current_user.hostel_ids
        and current_user.role != "super_admin"
    ):
        raise HTTPException(403, "Access denied to this hostel.")

    result = await db.execute(
        select(HostelImage).where(
            HostelImage.id == image_id,
            HostelImage.hostel_id == hostel_id,
        )
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(404, "Image not found.")

    await get_cloudinary_client().delete(img.url)
    await db.delete(img)
    await db.commit()
    return Response(status_code=204)
