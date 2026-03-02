#!/usr/bin/env python3
"""Compatibility wrapper for the terminology linter.

Deprecated: use src/tools/scripts/lint_terminology.py instead.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, cast


def _load_impl() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))
    return importlib.import_module("tools.scripts.lint_terminology")


def main() -> int:
    impl = _load_impl()
    filtered_args = [arg for arg in sys.argv[1:] if arg != "--check"]
    sys.argv = [sys.argv[0], *filtered_args]

    impl_main_obj = getattr(impl, "main")
    if not callable(impl_main_obj):
        raise RuntimeError("tools.scripts.lint_terminology.main is not callable")

    impl_main = cast(Callable[[], int], impl_main_obj)
    return impl_main()


if __name__ == "__main__":
    raise SystemExit(main())
