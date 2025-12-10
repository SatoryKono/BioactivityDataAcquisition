from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path
import sys
from typing import Iterable

import yaml


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            return p
    return start.resolve().parents[2]


ROOT = _find_project_root(Path(__file__))
SRC_DIR = ROOT / "src"
REGISTRY_PATH = ROOT / "src/bioetl/infrastructure/clients/base/abc_registry.yaml"
OUTPUT_PATH = ROOT / "docs/ABC_INDEX.md"


def load_registry(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Registry YAML must contain a mapping of names to targets.")
    return data


def load_class(target: str) -> type:
    module_name, class_name = target.rsplit(".", 1)
    module = importlib.import_module(module_name)
    try:
        cls = getattr(module, class_name)
        if not isinstance(cls, type):
            raise ImportError(
                f"Target {target!r} does not resolve to a class (got {type(cls).__name__})"
            )
        return cls
    except AttributeError as exc:  # pragma: no cover - explicit failure path
        raise ImportError(
            f"Class {class_name} not found in module {module_name}"
        ) from exc


def normalize_docstring(docstring: str | None) -> str:
    if not docstring:
        return "No docstring available."
    return " ".join(inspect.cleandoc(docstring).split())


def build_lines(entries: Iterable[tuple[str, str, str]]) -> list[str]:
    lines: list[str] = ["# ABC Index", "<!-- generated -->", ""]
    for name, target, description in entries:
        lines.append(f"- `{name}` — `{target}`")
        lines.append(f"  - {description}")
        lines.append("")
    return lines


def write_atomic(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def generate_index() -> None:
    sys.path.insert(0, str(SRC_DIR))
    registry = load_registry(REGISTRY_PATH)

    entries: list[tuple[str, str, str]] = []
    for name, target in registry.items():
        cls = load_class(target)
        description = normalize_docstring(cls.__doc__)
        entries.append((name, target, description))

    content = "\n".join(build_lines(entries)).rstrip() + "\n"
    write_atomic(OUTPUT_PATH, content)


if __name__ == "__main__":
    generate_index()

