from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path("src/bioetl")


def test_class_naming_suffixes() -> None:
    suffixes = (
        "Factory",
        "Service",
        "Transformer",
        "Error",
        "Config",
        "Protocol",
        "Port",
    )
    bad: list[str] = []
    for p in (SRC / "application").rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in [x for x in ast.walk(tree) if isinstance(x, ast.ClassDef)]:
            if not n.name.endswith(suffixes):
                bad.append(f"{p}:{n.name}")
    assert not bad, f"Class suffix violations: {bad}"


def test_module_naming_snake_case() -> None:
    bad: list[str] = []
    for p in SRC.rglob("*.py"):
        stem = p.stem
        if not re.fullmatch(r"[a-z][a-z0-9_]*", stem):
            bad.append(str(p))
        if stem in {"dw", "utils", "helpers", "misc"}:
            bad.append(str(p))
    assert not bad, f"Module naming violations: {bad}"


def test_constants_upper_snake_case() -> None:
    bad: list[str] = []
    for p in SRC.rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if (
                        isinstance(t, ast.Name)
                        and t.id.isupper() is False
                        and len(t.id) > 1
                    ):
                        if not t.id.startswith("__"):
                            bad.append(f"{p}:{t.id}")
    assert not bad, f"Constant naming violations: {bad}"
