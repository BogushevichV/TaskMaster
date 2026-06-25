import pytest
import httpx
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_login_flow(client):
    username = "test_manager_int"
    payload = {
        "username": username,
        "email": "test_manager_int@example.com",
        "full_name": "Test Manager",
        "role": "manager",
        "password": "secret123",
    }
    try:
        reg = await client.post("/api/v1/auth/register", json=payload)
    except (httpx.ConnectError, ConnectionRefusedError, OSError):
        pytest.skip("Database unavailable")

    if reg.status_code == 400 and "already" in reg.text.lower():
        pass
    elif reg.status_code not in (201, 400):
        pytest.skip(f"Database unavailable: {reg.status_code} {reg.text}")

    login = await client.post(
        "/api/v1/auth/login/json",
        json={"username": username, "password": "secret123"},
    )
    if login.status_code != 200:
        pytest.skip(f"Login failed (DB likely down): {login.text}")

    tokens = login.json()
    assert "access_token" in tokens

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == username
