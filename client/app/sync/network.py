from __future__ import annotations

import httpx

from client.app.api.client import ApiClient


def is_server_online(api: ApiClient) -> bool:
    health_url = api.base_url.replace("/api/v1", "") + "/health"
    try:
        response = api._client.get(health_url, timeout=3.0)
        return response.status_code == 200
    except (httpx.RequestError, OSError):
        return False
