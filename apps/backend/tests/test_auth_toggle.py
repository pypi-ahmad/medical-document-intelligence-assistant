"""Auth toggle behavior tests for local development."""

from app.config import settings


async def test_system_health_without_token_when_auth_disabled(client) -> None:
    original_enable_auth = settings.enable_auth
    try:
        settings.enable_auth = False
        response = await client.get("/api/system/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] in {"ok", "degraded"}
        assert "gpu_available" in payload
    finally:
        settings.enable_auth = original_enable_auth

