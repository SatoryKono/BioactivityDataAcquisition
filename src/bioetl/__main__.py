"""Entry point for running bioetl as a module: python -m bioetl."""

from __future__ import annotations

import contextlib
import importlib
import sys
from pathlib import Path


def _clear_known_stale_windows_bytecode() -> None:
    """Avoid stale shared-drive bytecode for runtime builder support imports."""
    if sys.platform != "win32":
        return

    stale_cache = (
        Path(__file__).resolve().parent
        / "composition"
        / "runtime_builders"
        / "__pycache__"
        / "_inputs_resolution_support.cpython-313.pyc"
    )
    with contextlib.suppress(OSError):
        stale_cache.unlink(missing_ok=True)
    importlib.invalidate_caches()


_clear_known_stale_windows_bytecode()

if __name__ == "__main__":
    from bioetl.interfaces.cli import main

    main()
