"""Request and response contracts exposed by the auth gateway."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AppRole = Literal["pending", "caregiver", "doctor", "admin"]


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str | None = None
    role: AppRole
    session_id: str = ""


class SignupRequest(BaseModel):
    email: str = Field(min_length=5)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthenticatedUser


class RoleUpdate(BaseModel):
    role: AppRole


class WebSocketTicketRequest(BaseModel):
    target: Literal["fusion", "feedback"]


class WebSocketTicketResponse(BaseModel):
    ticket: str
    expires_in: int = Field(ge=1)
