from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def _headers(self) -> dict[str, str]:
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        response = self._client.request(method, url, headers=self._headers(), **kwargs)
        if response.status_code == 401 and self.refresh_token and path != "/auth/refresh":
            if self._try_refresh():
                response = self._client.request(
                    method, url, headers=self._headers(), **kwargs
                )
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise ApiError(str(detail), response.status_code)
        if response.status_code == 204:
            return None
        if not response.content:
            return None
        return response.json()

    def _try_refresh(self) -> bool:
        try:
            data = self._client.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": self.refresh_token},
            ).json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            return True
        except Exception:
            return False

    def login(self, username: str, password: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/auth/login/json",
            json={"username": username, "password": password},
        )
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        return data

    def get_me(self) -> dict[str, Any]:
        return self._request("GET", "/auth/me")

    def list_tasks(
        self,
        *,
        status: str | None = None,
        assigned_to_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if assigned_to_id is not None:
            params["assigned_to_id"] = assigned_to_id
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if search:
            params["search"] = search
        return self._request("GET", "/tasks", params=params)

    def get_task(self, task_id: int) -> dict[str, Any]:
        return self._request("GET", f"/tasks/{task_id}")

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/tasks", json=payload)

    def update_task(self, task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/tasks/{task_id}", json=payload)

    def delete_task(self, task_id: int) -> None:
        self._request("DELETE", f"/tasks/{task_id}")

    def list_users(self, role: str | None = None) -> list[dict[str, Any]]:
        params = {"role": role} if role else {}
        return self._request("GET", "/users", params=params)

    def employees_metrics(self) -> list[dict[str, Any]]:
        return self._request("GET", "/users/employees/metrics")
