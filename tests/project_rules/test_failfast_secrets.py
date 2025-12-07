from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


def _iter_secret_fields(data: Any, prefix: str = ""):
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _iter_secret_fields(value, new_prefix)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            yield from _iter_secret_fields(item, f"{prefix}[{idx}]")
    else:
        yield prefix, data


def _looks_like_secret_key(path: str) -> bool:
    lowered = path.lower()
    return "secret" in lowered or lowered.endswith("key") or "token" in lowered


def test_configs_use_env_placeholders_for_secrets(configs_root: Path) -> None:
    violations: list[str] = []
    for path in configs_root.rglob("*.yaml"):
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}

        for field_path, value in _iter_secret_fields(data):
            if not _looks_like_secret_key(field_path):
                continue
            if isinstance(value, str) and "${" not in value:
                violations.append(f"{path.as_posix()}:{field_path} содержит захардкоженный секрет")

    if violations:
        pytest.fail("Секреты должны читаться из окружения:\n" + "\n".join(violations))

