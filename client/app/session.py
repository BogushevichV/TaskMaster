from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from client.app.api.client import ApiClient


@dataclass
class Session:
    api: ApiClient
    db_factory: Callable[[], Session]
    user: dict[str, Any] = field(default_factory=dict)

    @property
    def is_manager(self) -> bool:
        return self.user.get("role") == "manager"

    @property
    def user_id(self) -> int:
        return int(self.user["id"])

    @property
    def display_name(self) -> str:
        return self.user.get("full_name") or self.user.get("username", "")
