"""Configurable model routing for local Ollama tasks."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from app.config import settings
from app.services.infrastructure.gpu_monitor import gpu_has_headroom, probe_gpu
from app.services.infrastructure.ollama_client import OllamaClient, OllamaError


@dataclass(slots=True)
class RouteDecision:
    task: str
    selected_model: str
    candidates: list[str]
    reason: str
    gpu_available: bool


class ModelRouter:
    """Rule-based routing with fallback chain.

    Policy priorities:
    1. Task-specific preferred model.
    2. Local availability from Ollama model list.
    3. GPU headroom threshold for heavier models.
    4. Fallback list from settings.
    """

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self.ollama = ollama_client or OllamaClient()

    async def route(self, task: str) -> RouteDecision:
        candidates = self._candidate_chain(task)
        available_models: set[str] = set()
        reason = "fallback"
        with contextlib.suppress(OllamaError):
            available_models = set(await self.ollama.list_models())

        gpu_info = probe_gpu()
        gpu_available = bool(gpu_info.get("available"))
        has_headroom = gpu_has_headroom(required_mib=1800)

        for model in candidates:
            if available_models and model not in available_models:
                continue
            if self._is_heavy(model) and gpu_available and not has_headroom:
                continue
            reason = "task_policy"
            return RouteDecision(
                task=task,
                selected_model=model,
                candidates=candidates,
                reason=reason,
                gpu_available=gpu_available,
            )

        # If no candidate validated against availability, return top candidate
        # so caller can return explicit model-not-available error.
        return RouteDecision(
            task=task,
            selected_model=candidates[0],
            candidates=candidates,
            reason=reason,
            gpu_available=gpu_available,
        )

    def _candidate_chain(self, task: str) -> list[str]:
        task = task.lower().strip()
        preferred = {
            "qa": settings.default_chat_model,
            "chat": settings.default_chat_model,
            "summary": settings.summary_model,
            "entity_extraction": settings.entity_model,
            "timeline": settings.fast_chat_model,
            "report": settings.summary_model,
            "translation": settings.translation_model,
            "embedding": settings.embedding_model,
            "ocr": settings.ollama_glm_ocr_model,
        }.get(task, settings.default_chat_model)

        seen: set[str] = set()
        ordered: list[str] = []
        for model in [preferred, *settings.fallback_chat_model_list]:
            if model not in seen:
                seen.add(model)
                ordered.append(model)
        return ordered

    @staticmethod
    def _is_heavy(model: str) -> bool:
        heavy_markers = (":8b", ":9b", ":13b", "8b", "9b", "13b")
        model_l = model.lower()
        return any(marker in model_l for marker in heavy_markers)
