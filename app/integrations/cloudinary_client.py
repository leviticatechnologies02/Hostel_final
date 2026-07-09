"""
Cloudinary integration for file storage.
Supports proxy URLs for secure uploads/downloads to keep compatibility with S3.
Falls back to mock URLs when credentials are not configured.
"""
import uuid
import io
from typing import Optional
import cloudinary
import cloudinary.uploader

from app.config import get_settings


class CloudinaryClient:
    """Cloudinary client with graceful fallback when credentials are missing."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self.cloud_name = self._settings.cloudinary_cloud_name
        self.api_key = self._settings.cloudinary_api_key
        self.api_secret = self._settings.cloudinary_api_secret
        self._configured = bool(
            self.cloud_name
            and self.api_key
            and self.api_secret
            and self.cloud_name not in ("your-cloud-name", "")
            and self.api_key not in ("your-key", "")
            and self.api_secret not in ("your-secret", "")
        )

        if self._configured:
            cloudinary.config(
                cloud_name=self.cloud_name,
                api_key=self.api_key,
                api_secret=self.api_secret,
                secure=True,
            )

    def _mock_url(self, filename: str) -> str:
        return f"https://storage.stayease.dev/uploads/{filename}"

    async def get_presigned_upload_url(
        self,
        file_name: str,
        content_type: str,
        api_base_url: str = "",
    ) -> dict:
        unique_filename = f"{uuid.uuid4().hex}_{file_name}"
        
        # Build the proxy upload URL pointing to our backend route
        proxy_path = f"/api/v1/public/upload-proxy?filename={unique_filename}&content_type={content_type}"
        upload_url = f"{api_base_url}{proxy_path}" if api_base_url else proxy_path

        # Predict the final Cloudinary URL
        if not self._configured:
            file_url = self._mock_url(unique_filename)
        else:
            resource_type = "image" if content_type.startswith("image/") else "raw"
            file_url = f"https://res.cloudinary.com/{self.cloud_name}/{resource_type}/upload/stayease/{unique_filename}"

        return {
            "upload_url": upload_url,
            "file_url": file_url,
            "filename": unique_filename,
        }

    async def upload(
        self,
        file_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        if not self._configured:
            return self._mock_url(file_name)

        resource_type = "image" if content_type.startswith("image/") else "raw"
        try:
            public_id = f"stayease/{file_name}"
            # Strip extension for image public_id since Cloudinary manages extensions separately
            if resource_type == "image" and "." in public_id:
                public_id = public_id.rsplit(".", 1)[0]

            response = cloudinary.uploader.upload(
                io.BytesIO(content),
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True,
            )
            return response.get("secure_url")
        except Exception:
            return self._mock_url(file_name)

    async def delete(self, file_key: str) -> bool:
        if not self._configured:
            return True
        try:
            public_id = file_key
            # Extract public_id from URL if it's a full Cloudinary URL
            if "res.cloudinary.com" in file_key:
                parts = file_key.split("/upload/")
                if len(parts) > 1:
                    # Remove version if present (e.g. "v123456/stayease/file.jpg")
                    subparts = parts[1].split("/")
                    if subparts[0].startswith("v") and subparts[0][1:].isdigit():
                        public_id = "/".join(subparts[1:])
                    else:
                        public_id = parts[1]

            is_image = any(
                public_id.lower().endswith(ext)
                for ext in (".jpg", ".jpeg", ".png", ".webp")
            )
            if is_image and "." in public_id:
                public_id = public_id.rsplit(".", 1)[0]

            resource_type = "image" if is_image else "raw"
            result = cloudinary.uploader.destroy(
                public_id, resource_type=resource_type
            )
            return result.get("result") == "ok"
        except Exception:
            return False


_cloudinary_client: Optional[CloudinaryClient] = None


def get_cloudinary_client() -> CloudinaryClient:
    global _cloudinary_client
    if _cloudinary_client is None:
        _cloudinary_client = CloudinaryClient()
    return _cloudinary_client
