# Ollama Guide

## Required Local Models
- `glm-ocr:latest`
- `qwen3.5:4b`
- `qwen3.5:2b`
- `qwen3-embedding:4b`
- `phi4-mini:3.8b`
- `granite4.1:3b`
- optional fallbacks from config

## Commands

```bash
ollama list
ollama pull glm-ocr:latest
ollama pull qwen3.5:4b
ollama pull qwen3-embedding:4b
```

## Routing
Task-based model router chooses by policy + availability + GPU headroom and falls back safely.

## Best Practices
- Keep model names in config only.
- Monitor VRAM before scheduling heavy models.
- Pin embedding model for index + query consistency.
