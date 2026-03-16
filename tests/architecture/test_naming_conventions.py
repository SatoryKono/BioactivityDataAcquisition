from __future__ import annotations

import ast
import re
from pathlib import Path


def test_class_naming_suffixes(src_dir: Path, source_ast_cache: dict) -> None:
    suffixes = (
        "Factory",
        "Service",
        "Services",
        "Transformer",
        "Error",
        "Config",
        "Protocol",
        "Port",
        "Pipeline",
        "Result",
        "Extractor",
        "Manager",
        "Source",
        "Callback",
        "Analyzer",
        "Coordinator",
        "Runner",
        "Processor",
        "Validator",
        "Executor",
        "Aggregator",
        "Orderer",
        "Renamer",
        "Deduplicator",
        "Recorder",
        "Helper",
        "Schema",
        "Writer",
        "Observer",
        "Parser",
        "Utils",
        "Task",
        "Spec",
        "Group",
        "Context",
        "Summary",
        "Reason",
        "Planner",
        "Policy",
        "Resolver",
        "Generator",
        "Calculator",
        "Checker",
        "Mixin",
        "Callable",
        "Assembler",
    )
    app_path = src_dir / "bioetl" / "application"
    violations: list[str] = []
    for path, tree in source_ast_cache.items():
        if app_path not in path.parents:
            continue
        for node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            if node.name.startswith("_"):
                continue
            # Skip dataclass-style value objects (Info, Record, Status, Options, etc.)
            if any(
                node.name.endswith(s)
                for s in (
                    "Info",
                    "Record",
                    "Status",
                    "Options",
                    "State",
                    "Preview",
                    "Phase",
                    "Issue",
                    "Ids",
                    "Date",
                    "Identifiers",
                    "Classification",
                    "Signal",
                    "Affiliation",
                    "Author",
                    "Raw",
                    "Output",
                    "Outcome",
                    "Entry",
                    "Dependencies",
                )
            ):
                continue
            if not node.name.endswith(suffixes):
                violations.append(f"{path}:{node.lineno}:{node.name}")
    assert not violations, "Class naming violations:\n" + "\n".join(violations[:80])


def test_module_naming_snake_case(src_python_files: list) -> None:
    banned = {"dw.py", "helpers.py", "misc.py"}
    violations: list[str] = []
    for path in src_python_files:
        name = path.name
        if name in banned:
            violations.append(str(path))
        if not re.match(r"^[a-z0-9_]+\.py$", name):
            violations.append(str(path))
    assert not violations, "Module naming violations:\n" + "\n".join(violations[:80])


def test_constants_upper_snake_case(source_ast_cache: dict) -> None:
    violations: list[str] = []
    for path, tree in source_ast_cache.items():
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
