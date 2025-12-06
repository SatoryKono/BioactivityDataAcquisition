from __future__ import annotations

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "src/bioetl/infrastructure/clients/base/abc_registry.yaml"
INDEX_PATH = PROJECT_ROOT / "docs/ABC_INDEX.md"


def _load_registry_names() -> list[str]:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise AssertionError("Registry must be a mapping of ABC names to targets")
    return list(registry.keys())


def _parse_index_names(text: str) -> set[str]:
    pattern = re.compile(r"^- `([^`]+)`", flags=re.MULTILINE)
    return set(pattern.findall(text))


def test_registry_entries_are_listed_in_index() -> None:
    registry_names = _load_registry_names()
    index_text = INDEX_PATH.read_text(encoding="utf-8")
    index_names = _parse_index_names(index_text)

    missing = [name for name in registry_names if name not in index_names]
    assert not missing, f"Missing ABCs in index: {', '.join(missing)}"


def test_index_contains_generated_marker() -> None:
    index_text = INDEX_PATH.read_text(encoding="utf-8")
    assert "<!-- generated -->" in index_text
