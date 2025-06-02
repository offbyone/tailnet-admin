"""Data models for tailnet-admin."""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class User(BaseModel):
    """Tailscale user model."""

    id: str
    name: str
    email: str
    login_name: str
    admin: bool


class Device(BaseModel):
    """Tailscale device model."""

    id: str
    name: str
    addresses: List[str]
    user_id: str
    tags: Optional[List[str]] = None
    authorized: bool
    last_seen_at: Optional[str] = None
    os: Optional[str] = None
    created: str


class ACLRule(BaseModel):
    """Tailscale ACL rule model."""

    src: List[str]
    dst: List[str]
    action: str = "accept"