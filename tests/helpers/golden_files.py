"""Shared loaders for checked-in JSON golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


def load_json_fixture(path: Path) -> dict[str, Any]:
    """Load one checked-in JSON fixture as a mapping."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def load_named_json_fixture(base_dir: Path, name: str) -> dict[str, Any]:
    """Load ``<base_dir>/<name>.json``."""
    return load_json_fixture(base_dir / f"{name}.json")
