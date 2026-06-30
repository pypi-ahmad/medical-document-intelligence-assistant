"""Local Ollama HTTP client wrappers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings


class OllamaError(RuntimeError):
    pass


@dataclass(slots=True)
class OllamaGeneration:
    model: str
    content: str
    prompt_eval_count: int | None
    eval_count: int | None
    total_duration_ns: int | None


class OllamaClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 120.0) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise OllamaError(f"Ollama returned HTTP {response.status_code}")
            payload = response.json()
            return {
                "ok": True,
                "models": [item.get("name") for item in payload.get("models", [])],
                "count": len(payload.get("models", [])),
            }

    async def list_models(self) -> list[str]:
        health = await self.health()
        return [name for name in health["models"] if isinstance(name, str)]

    async def generate(
        self,
        *,
        model: str,
        prompt: str,
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> OllamaGeneration:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options or {"temperature": 0.1},
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
        except httpx.HTTPError as exc:
            raise OllamaError(f"Generation request failed: {exc}") from exc
        if response.status_code != 200:
            raise OllamaError(f"Generation failed with HTTP {response.status_code}: {response.text[:300]}")

        data = response.json()
        text = data.get("response")
        if not isinstance(text, str):
            raise OllamaError("Generation response missing 'response' text")
        return OllamaGeneration(
            model=model,
            content=text.strip(),
            prompt_eval_count=data.get("prompt_eval_count"),
            eval_count=data.get("eval_count"),
            total_duration_ns=data.get("total_duration"),
        )

    async def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": options or {"temperature": 0.1},
        }
        if system:
            payload["system"] = system

        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout_seconds) as client,
                client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response,
            ):
                if response.status_code != 200:
                    body = await response.aread()
                    raise OllamaError(
                        f"Generation stream failed with HTTP {response.status_code}: "
                        f"{body.decode('utf-8', errors='ignore')[:300]}"
                    )
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = item.get("response")
                    if isinstance(text, str) and text:
                        yield text
                    if item.get("done"):
                        break
        except httpx.HTTPError as exc:
            raise OllamaError(f"Generation stream request failed: {exc}") from exc

    async def embed(self, *, model: str, text: str) -> list[float]:
        payload = {"model": model, "prompt": text}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
        except httpx.HTTPError as exc:
            raise OllamaError(f"Embedding request failed: {exc}") from exc
        if response.status_code != 200:
            raise OllamaError(f"Embedding failed with HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
        embedding = data.get("embedding")
        if not isinstance(embedding, list):
            raise OllamaError("Embedding response missing 'embedding' list")
        return [float(v) for v in embedding]
