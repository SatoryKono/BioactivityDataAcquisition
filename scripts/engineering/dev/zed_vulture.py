#!/usr/bin/env python3
"""Zed-safe dead-code scan matching the architecture vulture gate.

Architecture test (``tests/architecture/test_layer_dependencies.py``)::

    vulture.scavenge([src/bioetl])
    get_unused_code(min_confidence=80)
    + name/type filters (ignore dunders, private names, reserved API params)

Bare ``python -m vulture src/bioetl`` uses confidence 60 by default and reports
thousands of false positives on Pandera schema fields, protocol methods, and
CLI entry surfaces. This wrapper applies the project filter so the Zed task is
actionable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BIOETL_PATH = REPO_ROOT / "src" / "bioetl"
MIN_CONFIDENCE = 80

# Keep aligned with tests/architecture/test_layer_dependencies.py
VULTURE_IGNORED_NAMES = {
    "__init__",
    "__str__",
    "__repr__",
    "__hash__",
    "__eq__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__aenter__",
    "__aexit__",
    "__enter__",
    "__exit__",
    "exc_type",
    "exc_val",
    "exc_value",
    "exc_tb",
    "traceback",
    "fullurl",
    "kind",
    "attributes",
    "links",
    "set_status_on_exception",
    "end_on_exit",
    "fetch",
    "write_bronze",
    "write_silver",
    "write_gold",
    "acquire",
    "release",
    "save_checkpoint",
    "load_checkpoint",
    "delete_checkpoint",
    "quarantine_record",
    "model_config",
    "main",
    "param",
    "execute",
    "awaitable",
}

RESERVED_API_PARAMS = {
    "overrides",
    "config_path",
    "watermark",
    "store_name",
    "from_phase",
    "allows_retry",
    "compensation_required",
    "degraded_mode_allowed",
}


def _is_reportable(item: object) -> bool:
    name = getattr(item, "name", "")
    filename = str(getattr(item, "filename", ""))
    item_type = getattr(item, "typ", "")
    confidence = int(getattr(item, "confidence", 0))
    if name in VULTURE_IGNORED_NAMES or name in RESERVED_API_PARAMS:
        return False
    if str(name).startswith("_"):
        return False
    if "test" in filename.lower():
        return False
    if item_type == "import" and confidence < 100:
        return False
    return item_type != "unreachable_code"


def _findings() -> list[object]:
    try:
        from vulture import Vulture
    except ImportError as exc:  # pragma: no cover - env bootstrap failure
        raise SystemExit(
            "[zed_vulture] vulture is required: uv sync --extra tests_full"
        ) from exc

    if not BIOETL_PATH.is_dir():
        raise SystemExit(f"[zed_vulture] source tree not found: {BIOETL_PATH}")

    vulture = Vulture()
    vulture.scavenge([str(BIOETL_PATH)])
    return [
        item
        for item in vulture.get_unused_code(min_confidence=MIN_CONFIDENCE)
        if _is_reportable(item)
    ]


def main(argv: list[str] | None = None) -> int:
    del argv
    os.chdir(REPO_ROOT)
    unused = _findings()
    print(
        f"[zed_vulture] path={BIOETL_PATH.as_posix()} "
        f"min_confidence={MIN_CONFIDENCE} reportable={len(unused)}",
        flush=True,
    )
    if not unused:
        print("[zed_vulture] no reportable dead-code findings", flush=True)
        return 0

    for item in unused:
        filename = getattr(item, "filename", "?")
        lineno = getattr(item, "first_lineno", "?")
        typ = getattr(item, "typ", "?")
        name = getattr(item, "name", "?")
        confidence = getattr(item, "confidence", "?")
        print(
            f"{filename}:{lineno}: unused {typ} '{name}' ({confidence}% confidence)",
            flush=True,
        )
    print(
        f"[zed_vulture] {len(unused)} reportable item(s) "
        "(architecture gate: test_dead_code_vulture)",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
