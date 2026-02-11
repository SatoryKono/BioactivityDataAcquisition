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
    violations: list[str] = []
    for path in (SRC / "application").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            if node.name.startswith("_"):
                continue
            if not node.name.endswith(suffixes):
                violations.append(f"{path}:{node.lineno}:{node.name}")
    assert not violations, "Class naming violations:\n" + "\n".join(violations[:80])


def test_module_naming_snake_case() -> None:
    banned = {"dw.py", "utils.py", "helpers.py", "misc.py"}
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        name = path.name
        if name in banned:
            violations.append(str(path))
        if not re.match(r"^[a-z0-9_]+\.py$", name):
            violations.append(str(path))
    assert not violations, "Module naming violations:\n" + "\n".join(violations[:80])


def test_constants_upper_snake_case() -> None:
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if name.startswith("_"):
                            continue
                        if name.isupper() or name[0].isupper():
                            continue
                        if isinstance(
                            node.value,
                            (ast.Constant, ast.Tuple, ast.List, ast.Dict, ast.Set),
                        ):
                            violations.append(f"{path}:{node.lineno}:{name}")
    assert not violations, "Constant naming violations:\n" + "\n".join(violations[:80])
