import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceResponse(BaseModel):
    id: uuid.UUID
    browser: str | None = None
    operating_system: str | None = None
    ip_address: str | None = None
    geographic_location: str | None = None
    last_active_at: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    is_revoked: bool
    is_used: bool
    expires_at: datetime
    created_at: datetime
    device: DeviceResponse | None = None

    class Config:
        from_attributes = True


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True
