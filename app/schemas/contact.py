from pydantic import BaseModel, EmailStr, Field


class ContactLeadCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    organization_name: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=10, max_length=5000)
    
    # These fields are currently not in the UI, but we'll include them as optional
    inquiry_type: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)


class ContactLeadResponse(BaseModel):
    message: str
