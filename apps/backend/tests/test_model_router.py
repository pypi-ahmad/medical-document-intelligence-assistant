import pytest

from app.services.infrastructure.model_router import ModelRouter


class _StubOllama:
    async def list_models(self) -> list[str]:
        return ["qwen3.5:4b", "phi4-mini:3.8b", "qwen3-embedding:4b", "glm-ocr:latest"]


@pytest.mark.asyncio
async def test_model_router_selects_available_task_model() -> None:
    router = ModelRouter(ollama_client=_StubOllama())
    decision = await router.route("qa")

    assert decision.selected_model in decision.candidates
    assert decision.selected_model == "qwen3.5:4b"
    assert decision.task == "qa"
