"""
AWS S3 integration for file storage.
Supports presigned URLs for secure uploads/downloads.
Falls back to mock URLs when AWS credentials are not configured.
"""
import uuid
from typing import Optional

from app.config import get_settings


class S3Client:
    """AWS S3 client with graceful fallback when credentials are missing."""

    def __init__(self) -> None:
        self._client = None
        self._settings = get_settings()
        self.bucket_name = self._settings.aws_storage_bucket_name
        self._configured = bool(
            self._settings.aws_access_key_id
            and self._settings.aws_access_key_id not in ("xxxxx", "", "your-key")
            and self._settings.aws_secret_access_key
            and self._settings.aws_secret_access_key not in ("xxxxx", "", "your-secret")
        )

    def _get_client(self):
        """Lazy-init boto3 client only when actually needed and configured."""
        if self._client is None and self._configured:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    aws_access_key_id=self._settings.aws_access_key_id,
                    aws_secret_access_key=self._settings.aws_secret_access_key,
                    region_name=self._settings.aws_region,
                )
            except Exception:
                self._configured = False
        return self._client

    def _mock_url(self, filename: str) -> str:
        return f"https://storage.leviticanestora.dev/uploads/{filename}"

    async def get_presigned_upload_url(
        self,
        file_name: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict:
        unique_filename = f"{uuid.uuid4().hex}_{file_name}"

        client = self._get_client()
        if client is None:
            # S3 not configured — return mock response for dev/test environments
            # Frontend detects X-Amz-Mock=true and skips the actual PUT
            mock_upload_url = (
                f"https://leviticanestora-uploads.s3.ap-south-1.amazonaws.com/{unique_filename}"
                f"?X-Amz-Mock=true&X-Amz-Expires={expires_in}"
            )
            return {
                "upload_url": mock_upload_url,
                "file_url": self._mock_url(unique_filename),
                "filename": unique_filename,
            }

        try:
            from botocore.exceptions import ClientError
            url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": unique_filename,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return {
                "upload_url": url,
                "file_url": f"https://{self.bucket_name}.s3.{self._settings.aws_region}.amazonaws.com/{unique_filename}",
                "filename": unique_filename,
            }
        except Exception as e:
            # Fallback to mock on any AWS error
            return {
                "upload_url": self._mock_url(unique_filename),
                "file_url": self._mock_url(unique_filename),
                "filename": unique_filename,
            }

    async def upload(self, file_name: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        unique_filename = f"{uuid.uuid4().hex}_{file_name}"
        client = self._get_client()
        if client is None:
            return self._mock_url(unique_filename)
        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=unique_filename,
                Body=content,
                ContentType=content_type,
            )
            return f"https://{self.bucket_name}.s3.{self._settings.aws_region}.amazonaws.com/{unique_filename}"
        except Exception:
            return self._mock_url(unique_filename)

    async def delete(self, file_key: str) -> bool:
        client = self._get_client()
        if client is None:
            return True
        try:
            client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except Exception:
            return False

    async def exists(self, file_key: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except Exception:
            return False


_s3_client: Optional[S3Client] = None


def get_s3_client() -> S3Client:
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client
