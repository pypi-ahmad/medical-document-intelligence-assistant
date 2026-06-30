"""Compatibility wrapper for ``scripts/eval_diff.py``.

Backend tests import ``scripts.eval_diff`` with ``PYTHONPATH=apps``.
This shim delegates to the repository root script implementation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_root_module() -> ModuleType:
    root_script = Path(__file__).resolve().parents[2] / "scripts" / "eval_diff.py"
    spec = importlib.util.spec_from_file_location("root_eval_diff", root_script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load eval_diff script from {root_script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(runs_dir: str = "eval/runs") -> int:
    module: Any = _load_root_module()
    return int(module.main(runs_dir))


if __name__ == "__main__":
    raise SystemExit(main())

