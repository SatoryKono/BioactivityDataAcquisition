#!/usr/bin/env python3
"""Shared compatibility helpers for top-level ``scripts/docs`` shims."""

from __future__ import annotations

import sys
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Any

_SHIM_METADATA_NAMES = {
    "__name__",
    "__package__",
    "__loader__",
    "__spec__",
    "__builtins__",
    "__cached__",
    "__file__",
}


def _ensure_repo_imports(*, include_src: bool) -> None:
    """Ensure repo-local packages are importable for direct script execution."""
    repo_root = Path(__file__).resolve().parents[2]
    search_paths = [repo_root]
    if include_src:
        search_paths.append(repo_root / "src")
    for path in reversed(search_paths):
        resolved = str(path)
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


def _load_module(module_name: str, *, include_src: bool):
    _ensure_repo_imports(include_src=include_src)
    return import_module(module_name)


def load_main(module_name: str, *, include_src: bool = True) -> Any:
    """Return ``main`` from the packaged implementation module."""
    module = _load_module(module_name, include_src=include_src)
    return module.main


def load_public_api(
    target_globals: dict[str, Any],
    module_name: str,
    *,
    include_src: bool = True,
) -> Any:
    """Expose the packaged module public surface through a compatibility shim."""
    _ensure_repo_imports(include_src=include_src)
    module = _load_module(module_name, include_src=include_src)
    spec = module.__spec__
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(module_name)

    impl_path = Path(spec.origin)
    shim_file = target_globals.get("__file__")
    shim_package = target_globals.get("__package__")
    target_globals["__file__"] = str(impl_path)
    target_globals["__package__"] = module_name.rpartition(".")[0]
    try:
        exec(
            compile(impl_path.read_text(encoding="utf-8"), str(impl_path), "exec"),
            target_globals,
        )
    finally:
        if shim_file is not None:
            target_globals["__file__"] = shim_file
        if "__package__" in target_globals:
            target_globals["__package__"] = shim_package

    if "__all__" in target_globals:
        target_globals["__all__"] = list(target_globals["__all__"])
    return module
