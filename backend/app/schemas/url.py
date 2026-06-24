import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class URLCreate(BaseModel):
    target_url: str = Field(..., max_length=4096)
    custom_alias: str | None = Field(default=None, min_length=3, max_length=64)
    expires_at: datetime | None = None
    title: str | None = Field(default=None, max_length=255)

    @field_validator("target_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("target_url must start with http:// or https://")
        if len(v) < 10:
            raise ValueError("target_url is too short to be valid")
        return v

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.isalnum():
            raise ValueError("custom_alias must be alphanumeric")
        return v


class URLUpdate(BaseModel):
    target_url: str | None = Field(default=None, max_length=4096)
    expires_at: datetime | None = None
    is_active: bool | None = None
    title: str | None = Field(default=None, max_length=255)


class URLRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    short_code: str
    custom_alias: str | None
    target_url: str
    title: str | None
    created_at: datetime
    expires_at: datetime | None
    is_active: bool
    total_clicks: int
    short_url: str


class URLListResponse(BaseModel):
    items: list[URLRead]
    total: int
    page: int
    page_size: int
    total_pages: int
