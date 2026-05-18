from pydantic import BaseModel, Field, field_validator

class PresignedUploadRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=120)
    file_size: int = Field(gt=0)  # Remove le constraint here, handle in service

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        # Just ensure it's positive, we'll validate the limit in the service
        if v <= 0:
            raise ValueError("File size must be greater than 0")
        return v


class PresignedUploadResponse(BaseModel):
    upload_url: str
    file_url: str
    filename: str
