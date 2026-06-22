from __future__ import annotations

import httpx

from client.app.api.client import ApiClient, ApiError
from client.app.db.sync_ops import (
    queue_offline_create,
    queue_offline_delete,
    queue_offline_update,
)
from client.app.sync.network import is_server_online


class TaskService:
    def __init__(self, session) -> None:
        self.session = session

    @property
    def api(self) -> ApiClient:
        return self.session.api

    def online(self) -> bool:
        return is_server_online(self.api)

    def create_task(self, payload: dict, *, assignee_name: str | None = None) -> dict | None:
        try:
            if not self.online():
                raise OSError("offline")
            return self.api.create_task(payload)
        except (ApiError, httpx.RequestError, OSError):
            db = self.session.db_factory()
            try:
                offline_payload = dict(payload)
                if assignee_name:
                    offline_payload["_assignee_name"] = assignee_name
                task_id = queue_offline_create(db, offline_payload)
                return {"id": task_id, **payload, "_offline": True}
            finally:
                db.close()

    def update_task(self, task_id: int, payload: dict) -> dict | None:
        try:
            if not self.online():
                raise OSError("offline")
            return self.api.update_task(task_id, payload)
        except (ApiError, httpx.RequestError, OSError):
            db = self.session.db_factory()
            try:
                queue_offline_update(db, task_id, payload)
                return {"id": task_id, **payload, "_offline": True}
            finally:
                db.close()

    def delete_task(self, task_id: int) -> None:
        try:
            if not self.online():
                raise OSError("offline")
            self.api.delete_task(task_id)
        except (ApiError, httpx.RequestError, OSError):
            db = self.session.db_factory()
            try:
                queue_offline_delete(db, task_id)
            finally:
                db.close()
