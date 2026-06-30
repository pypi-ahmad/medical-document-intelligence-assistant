# GPU Guide

## Hardware Target
NVIDIA RTX 4060 Laptop GPU (8GB VRAM), CUDA-enabled.

## Runtime Behavior
- Detects GPU via `nvidia-smi`.
- Uses GPU-friendly model routing when headroom exists.
- Falls back to CPU when unavailable or memory-constrained.

## Verification

```bash
nvidia-smi
curl http://localhost:8000/api/system/health
```

## Memory Optimization
- Prefer 2B-4B models for chat/summary
- Limit concurrent heavy jobs
- Constrain prompt/context sizes
- Use embedding model separately from generation model
