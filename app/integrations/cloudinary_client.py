"""
app/integrations/cloudinary_client.py

Cloudinary integration for file storage.
All uploads go directly to Cloudinary — no presigned URL indirection needed.
"""
import logging
import uuid
import io
from typing import Optional

import cloudinary
import cloudinary.uploader
import cloudinary.api

from app.config import get_settings

logger = logging.getLogger(__name__)


class CloudinaryClient:
    """Cloudinary client with proper error logging and no silent fallbacks."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self.cloud_name   = self._settings.cloudinary_cloud_name
        self.api_key      = self._settings.cloudinary_api_key
        self.api_secret   = self._settings.cloudinary_api_secret

        self._configured = bool(
            self.cloud_name
            and self.api_key
            and self.api_secret
            and self.cloud_name  not in ("your-cloud-name", "")
            and self.api_key     not in ("your-key", "")
            and self.api_secret  not in ("your-secret", "")
        )

        if self._configured:
            cloudinary.config(
                cloud_name=self.cloud_name,
                api_key=self.api_key,
                api_secret=self.api_secret,
                secure=True,
            )
            logger.info("✅ Cloudinary configured for cloud '%s'", self.cloud_name)
        else:
            logger.warning(
                "⚠️  Cloudinary credentials not set — uploads will return placeholder URLs. "
                "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET."
            )

    def _mock_url(self, filename: str) -> str:
        """Placeholder URL used when Cloudinary is not configured (local dev only)."""
        return f"https://placeholder.stayease.dev/uploads/{filename}"

    def _resource_type(self, content_type: str) -> str:
        """Derive Cloudinary resource_type from MIME type."""
        ct = content_type.lower()
        if ct.startswith("image/"):
            return "image"
        if ct == "application/pdf":
            return "raw"
        if ct.startswith("video/"):
            return "video"
        return "raw"

    def _public_id(self, file_name: str, resource_type: str) -> str:
        """
        Build a stable Cloudinary public_id.
        For images Cloudinary auto-appends the extension, so we strip it from the public_id.
        For raw files (PDF etc.) we keep the extension so the URL is predictable.
        """
        pid = f"stayease/{file_name}"
        if resource_type == "image" and "." in pid:
            pid = pid.rsplit(".", 1)[0]
        return pid

    # ─────────────────────────────────────────────────────────────
    # UPLOAD
    # ─────────────────────────────────────────────────────────────

    async def upload(
        self,
        file_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload binary content to Cloudinary and return the permanent secure_url.

        Args:
            file_name: Logical path/name, e.g. "profile/user123/photo.jpg"
            content:   Raw file bytes.
            content_type: MIME type — used to set Cloudinary resource_type.

        Returns:
            The permanent https://res.cloudinary.com/… URL.

        Raises:
            RuntimeError: if Cloudinary is configured but the upload fails.
        """
        if not self._configured:
            logger.debug("Cloudinary not configured, returning placeholder for '%s'", file_name)
            return self._mock_url(file_name)

        rtype = self._resource_type(content_type)
        pid   = self._public_id(file_name, rtype)

        logger.debug("Uploading '%s' to Cloudinary (resource_type=%s, public_id=%s)", file_name, rtype, pid)

        try:
            response = cloudinary.uploader.upload(
                io.BytesIO(content),
                public_id=pid,
                resource_type=rtype,
                overwrite=True,
                unique_filename=False,
            )
            url = response.get("secure_url", "")
            if not url:
                raise RuntimeError("Cloudinary returned empty secure_url")
            logger.info("✅ Uploaded '%s' → %s", file_name, url)
            return url

        except Exception as exc:
            logger.error("❌ Cloudinary upload failed for '%s': %s", file_name, exc, exc_info=True)
            raise RuntimeError(f"File upload failed: {exc}") from exc

    # ─────────────────────────────────────────────────────────────
    # PRESIGNED URL  (legacy — kept for backwards compat)
    # ─────────────────────────────────────────────────────────────

    async def get_presigned_upload_url(
        self,
        file_name: str,
        content_type: str,
        api_base_url: str = "",
    ) -> dict:
        """
        Generate a proxy upload URL that points to our own backend.
        This is the legacy 2-step flow; prefer `upload()` with UploadFile directly.
        """
        unique_filename = f"{uuid.uuid4().hex}_{file_name}"
        proxy_path = (
            f"/api/v1/public/upload-proxy"
            f"?filename={unique_filename}&content_type={content_type}"
        )
        upload_url = f"{api_base_url}{proxy_path}" if api_base_url else proxy_path

        if not self._configured:
            file_url = self._mock_url(unique_filename)
        else:
            rtype    = self._resource_type(content_type)
            file_url = (
                f"https://res.cloudinary.com/{self.cloud_name}"
                f"/{rtype}/upload/stayease/{unique_filename}"
            )

        return {
            "upload_url": upload_url,
            "file_url":   file_url,
            "filename":   unique_filename,
        }

    # ─────────────────────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────────────────────

    async def delete(self, file_key: str) -> bool:
        """
        Delete a file from Cloudinary by URL or public_id.
        Returns True on success, False otherwise (never raises).
        """
        if not self._configured:
            return True

        try:
            public_id = file_key

            if "res.cloudinary.com" in file_key:
                # Extract public_id from the full URL
                parts = file_key.split("/upload/")
                if len(parts) > 1:
                    subparts = parts[1].split("/")
                    # Strip optional version segment like "v1234567/"
                    if subparts[0].startswith("v") and subparts[0][1:].isdigit():
                        public_id = "/".join(subparts[1:])
                    else:
                        public_id = parts[1]

            # Strip query-strings if any
            public_id = public_id.split("?")[0]

            is_image = any(
                public_id.lower().endswith(ext)
                for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
            )
            if is_image and "." in public_id:
                public_id = public_id.rsplit(".", 1)[0]

            rtype = "image" if is_image else "raw"
            result = cloudinary.uploader.destroy(public_id, resource_type=rtype)
            success = result.get("result") == "ok"
            if success:
                logger.info("✅ Deleted Cloudinary asset '%s'", public_id)
            else:
                logger.warning("⚠️  Cloudinary delete returned '%s' for '%s'", result, public_id)
            return success

        except Exception as exc:
            logger.error("❌ Cloudinary delete failed for '%s': %s", file_key, exc, exc_info=True)
            return False


# ─────────────────────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────────────────────

_cloudinary_client: Optional[CloudinaryClient] = None


def get_cloudinary_client() -> CloudinaryClient:
    global _cloudinary_client
    if _cloudinary_client is None:
        _cloudinary_client = CloudinaryClient()
    return _cloudinary_client
