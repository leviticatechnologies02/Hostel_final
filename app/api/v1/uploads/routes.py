"""
app/api/v1/uploads/routes.py

Centralized file upload endpoints that are fully testable in Swagger UI.
Uses FastAPI's UploadFile for proper multipart/form-data support.
All uploads go directly to Cloudinary.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.dependencies import DBSession, CurrentUser, require_roles
from app.integrations.cloudinary_client import get_cloudinary_client

router = APIRouter()

AnyAuthUser = Annotated[
    CurrentUser,
    Depends(require_roles("visitor", "student", "hostel_admin", "supervisor", "super_admin")),
]
AdminUser = Annotated[CurrentUser, Depends(require_roles("hostel_admin", "super_admin"))]
StudentUser = Annotated[CurrentUser, Depends(require_roles("student"))]
VisitorUser = Annotated[CurrentUser, Depends(require_roles("visitor"))]
SupervisorUser = Annotated[CurrentUser, Depends(require_roles("supervisor", "hostel_admin", "super_admin"))]

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_DOC_TYPES   = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
_MAX_IMG_MB  = 5
_MAX_DOC_MB  = 10

def _validate(content: bytes, ct: str, allowed: set, max_mb: int, label: str) -> None:
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(400, f"{label} exceeds {max_mb} MB limit.")
    if ct.lower() not in allowed:
        raise HTTPException(400, f"Unsupported file type '{ct}'. Allowed: {', '.join(sorted(allowed))}.")


# ─────────────────────────────────────────────────────────────
# 1. PROFILE PICTURE  (all authenticated users)
# ─────────────────────────────────────────────────────────────

@router.post(
    "/profile-picture",
    summary="Upload profile picture",
    tags=["Uploads"],
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
    - The returned `url` should be stored as `profile_picture_url` via the profile update endpoint.
    """
    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _IMAGE_TYPES, _MAX_IMG_MB, "Profile picture")

    url = await get_cloudinary_client().upload(
        file_name=f"profile/{current_user.id}/{file.filename}",
        content=content,
        content_type=ct,
    )
    # Auto-update user profile_picture_url
    from sqlalchemy import select, update as sa_update
    from app.models.user import User
    await db.execute(
        sa_update(User).where(User.id == current_user.id).values(profile_picture_url=url)
    )
    await db.commit()
    return {"url": url, "filename": file.filename, "status": "success"}


# ─────────────────────────────────────────────────────────────
# 2. ID DOCUMENT  (visitor / student)
# ─────────────────────────────────────────────────────────────

@router.post(
    "/id-document",
    summary="Upload ID document",
    tags=["Uploads"],
)
async def upload_id_document(
    current_user: AnyAuthUser,
    file: UploadFile = File(..., description="ID proof — JPEG / PNG / WebP / PDF (max 10 MB)"),
):
    """
    Upload an ID document (Aadhaar, Passport, etc.) for the visitor.

    - Accepted types: **JPEG, PNG, WebP, PDF**
    - Max size: **10 MB**
    - Returns `url` — pass this as `id_document_url` in the booking applicant patch request.
    """
    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _DOC_TYPES, _MAX_DOC_MB, "ID document")

    url = await get_cloudinary_client().upload(
        file_name=f"id-docs/{current_user.id}/{file.filename}",
        content=content,
        content_type=ct,
    )
    return {"url": url, "filename": file.filename, "content_type": ct, "status": "success"}


# ─────────────────────────────────────────────────────────────
# 3. COMPLAINT ATTACHMENT  (student)
# ─────────────────────────────────────────────────────────────

@router.post(
    "/complaint-attachment",
    summary="Upload complaint attachment",
    tags=["Uploads"],
)
async def upload_complaint_attachment(
    current_user: AnyAuthUser,
    file: UploadFile = File(..., description="Complaint attachment — JPEG / PNG / WebP / PDF (max 10 MB)"),
):
    """
    Upload an image or document to attach to a complaint.

    - Accepted types: **JPEG, PNG, WebP, PDF**
    - Max size: **10 MB**
    - Returns `url` — pass this as `attachment_url` when creating a complaint.
    """
    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _DOC_TYPES, _MAX_DOC_MB, "Attachment")

    url = await get_cloudinary_client().upload(
        file_name=f"complaints/{current_user.id}/{file.filename}",
        content=content,
        content_type=ct,
    )
    return {"url": url, "filename": file.filename, "content_type": ct, "status": "success"}


# ─────────────────────────────────────────────────────────────
# 4. HOSTEL IMAGE  (hostel_admin / super_admin)
# ─────────────────────────────────────────────────────────────

@router.post(
    "/hostel-image/{hostel_id}",
    summary="Upload hostel image",
    tags=["Uploads"],
    status_code=201,
)
async def upload_hostel_image(
    hostel_id: str,
    current_user: AdminUser,
    db: DBSession,
    file: UploadFile = File(..., description="Hostel image — JPEG / PNG / WebP (max 5 MB)"),
    caption: str = Form(None, description="Optional caption for this image"),
    image_type: str = Form("gallery", description="Image type: 'gallery', 'exterior', 'interior', 'room', 'amenity'"),
    is_primary: bool = Form(False, description="Set as the primary/cover image"),
):
    """
    Upload an image for a specific hostel.

    - Accepted types: **JPEG, PNG, WebP**
    - Max size: **5 MB**
    - The image is stored in the `hostel_images` table and returned in hostel detail responses.
    """
    from app.models.hostel import HostelImage
    from sqlalchemy import select, func

    # Permission check
    if hostel_id not in current_user.hostel_ids and current_user.role != "super_admin":
        raise HTTPException(403, "Access denied to this hostel.")

    content = await file.read()
    ct = (file.content_type or "").lower()
    _validate(content, ct, _IMAGE_TYPES, _MAX_IMG_MB, "Hostel image")

    url = await get_cloudinary_client().upload(
        file_name=f"hostels/{hostel_id}/{file.filename}",
        content=content,
        content_type=ct,
    )

    # Determine sort order
    result = await db.execute(
        select(func.coalesce(func.max(HostelImage.sort_order), -1)).where(
            HostelImage.hostel_id == hostel_id
        )
    )
    next_sort = (result.scalar() or -1) + 1

    # If this is primary, unset any existing primary
    if is_primary:
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(HostelImage)
            .where(HostelImage.hostel_id == hostel_id)
            .values(is_primary=False)
        )

    img = HostelImage(
        hostel_id=hostel_id,
        url=url,
        thumbnail_url=url,       # Cloudinary auto-generates thumbnails on fetch
        caption=caption,
        image_type=image_type,
        sort_order=next_sort,
        is_primary=is_primary,
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)

    return {
        "id": img.id,
        "url": img.url,
        "thumbnail_url": img.thumbnail_url,
        "caption": img.caption,
        "image_type": img.image_type,
        "sort_order": img.sort_order,
        "is_primary": img.is_primary,
        "status": "success",
    }


@router.delete(
    "/hostel-image/{hostel_id}/{image_id}",
    summary="Delete hostel image",
    tags=["Uploads"],
    status_code=204,
)
async def delete_hostel_image(
    hostel_id: str,
    image_id: str,
    current_user: AdminUser,
    db: DBSession,
):
    """
    Delete a hostel image from both Cloudinary and the database.
    """
    from app.models.hostel import HostelImage
    from sqlalchemy import select
    from starlette.responses import Response

    if hostel_id not in current_user.hostel_ids and current_user.role != "super_admin":
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

    # Delete from Cloudinary
    await get_cloudinary_client().delete(img.url)

    await db.delete(img)
    await db.commit()
    return Response(status_code=204)
