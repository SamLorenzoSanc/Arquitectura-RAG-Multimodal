from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class IdentityUser:
    id: UUID | str
    name: str
    email: str
    active: bool = True
    password_hash: str | None = None


@dataclass
class Credentials:
    email: str
    password: str
    name: str | None = None


@dataclass
class AccessToken:
    token: str
    expires_in: int
    token_type: str = "Bearer"


@dataclass
class Profile:
    user_id: str
    name: str
    email: str
    data: dict[str, Any] = field(default_factory=dict)
