from __future__ import annotations

import pytest

from app.config import settings
from app.main import _load_persisted_model_config
from app.models.medical_db_models import SystemSetting
from tests.conftest import _test_session_maker


@pytest.mark.asyncio
async def test_load_persisted_model_config_updates_runtime_settings(monkeypatch) -> None:
    originals = {
        "default_chat_model": settings.default_chat_model,
        "fast_chat_model": settings.fast_chat_model,
        "summary_model": settings.summary_model,
        "entity_model": settings.entity_model,
        "embedding_model": settings.embedding_model,
        "translation_model": settings.translation_model,
        "fallback_chat_models": settings.fallback_chat_models,
    }
    monkeypatch.setattr("app.main.async_session", _test_session_maker)

    try:
        async with _test_session_maker() as db:
            db.add(
                SystemSetting(
                    key="model_config",
                    value_json={
                        "default_chat_model": "phi4-mini:3.8b",
                        "fast_chat_model": "qwen3.5:2b",
                        "summary_model": "granite4.1:3b",
                        "entity_model": "qwen3.5:4b",
                        "embedding_model": "qwen3-embedding:4b",
                        "translation_model": "translategemma:4b",
                        "fallback_chat_models": ["phi4-mini:3.8b", "ministral-3:3b"],
                    },
                )
            )
            await db.commit()

        await _load_persisted_model_config()

        assert settings.default_chat_model == "phi4-mini:3.8b"
        assert settings.fast_chat_model == "qwen3.5:2b"
        assert settings.summary_model == "granite4.1:3b"
        assert settings.entity_model == "qwen3.5:4b"
        assert settings.embedding_model == "qwen3-embedding:4b"
        assert settings.translation_model == "translategemma:4b"
        assert settings.fallback_chat_model_list == ["phi4-mini:3.8b", "ministral-3:3b"]
    finally:
        settings.default_chat_model = originals["default_chat_model"]
        settings.fast_chat_model = originals["fast_chat_model"]
        settings.summary_model = originals["summary_model"]
        settings.entity_model = originals["entity_model"]
        settings.embedding_model = originals["embedding_model"]
        settings.translation_model = originals["translation_model"]
        settings.fallback_chat_models = originals["fallback_chat_models"]
