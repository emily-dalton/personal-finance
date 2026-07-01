from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PlanCreate(BaseModel):
    name: str = "My plan"
    state_json: str = "{}"


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    state_json: Optional[str] = None


class PlanResponse(BaseModel):
    id: str
    name: str
    state_json: str
    share_token: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShareResponse(BaseModel):
    share_token: str
    share_url: str


class MessageResponse(BaseModel):
    message: str
