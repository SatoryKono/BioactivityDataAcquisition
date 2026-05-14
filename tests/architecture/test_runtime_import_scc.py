"""Architecture regression tests for runtime import SCC drift."""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

SRC_ROOT = Path("src/bioetl")
FORBIDDEN_RUNTIME_SCCS: tuple[frozenset[str], ...] = (
    frozenset(
        {
            "bioetl.domain.control_plane.run_ledger",
            "bioetl.domain.control_plane.run_ledger_replay",
        }
    ),
    frozenset(
        {
            "bioetl.application.core._record_normalization_runtime_support",
            "bioetl.application.core.record_normalization_processor",
        }
    ),
    frozenset(
        {
            "bioetl.domain.behavior._dq_rule_evaluators",
            "bioetl.domain.behavior._dq_rule_evaluators_cross",
        }
    ),
    frozenset(
        {
            "bioetl.domain.control_plane._reproducibility_profile_builders",
            "bioetl.domain.control_plane.reproducibility_profiles",
        }
    ),
    frozenset(
        {
            "bioetl.composition._services",
            "bioetl.composition._workflow_services",
        }
    ),
    frozenset(
        {
            "bioetl.application.composite.checkpoint._state_support",
            "bioetl.application.composite.checkpoint.state",
        }
    ),
)


def _module_name_from_path(path: Path) -> str:
    rel = path.relative_to(SRC_ROOT)
    parts = ["bioetl", *rel.parts]
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = Path(parts[-1]).stem
    return ".".join(parts)


def _iter_modules() -> dict[str, Path]:
    return {
        _module_name_from_path(path): path
        for path in sorted(SRC_ROOT.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def _resolve_relative_import(
    source_module: str,
    level: int,
    module: str | None,
) -> list[str] | list[object]:
    package_parts = source_module.split(".")[:-1]
    depth = max(level - 1, 0)
    if depth > len(package_parts):
        return []
    base = package_parts if depth == 0 else package_parts[:-depth]
    if module:
        return [".".join([*base, module])]
    return base


def _import_targets(node: ast.AST, source_module: str) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.level == 0:
        if not node.module:
            return []
        targets = [node.module]
        if node.module == "bioetl":
            targets.extend(
                f"bioetl.{alias.name}" for alias in node.names if alias.name != "*"
            )
        return targets
    if node.module:
        return list(_resolve_relative_import(source_module, node.level, node.module))
    base_parts = list(_resolve_relative_import(source_module, node.level, None))
    return [
        ".".join([*base_parts, alias.name]) for alias in node.names if alias.name != "*"
    ]


def _build_runtime_import_graph() -> dict[str, set[str]]:
    modules = _iter_modules()
    edges: dict[str, set[str]] = defaultdict(set)
    for module_name, path in modules.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents: dict[ast.AST, ast.AST | None] = {tree: None}
        stack = [tree]
        while stack:
            node = stack.pop()
            for child in ast.iter_child_nodes(node):
                parents[child] = node
                stack.append(child)

        def _inside_type_checking(node: ast.AST) -> bool:
            current: ast.AST | None = node
            while current is not None:
                if isinstance(current, ast.If):
                    test = current.test
                    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                        return True
                    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
                        return True
                current = parents.get(current)
            return False

        for node in ast.walk(tree):
            if _inside_type_checking(node):
                continue
            for target in _import_targets(node, module_name):
                if target in modules:
                    edges[module_name].add(target)
    return edges


def _iter_runtime_sccs(edges: dict[str, set[str]]) -> Iterable[frozenset[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low_links: dict[str, int] = {}

    def strongconnect(node: str) -> Iterable[frozenset[str]]:
        nonlocal index
        indices[node] = index
        low_links[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in edges.get(node, set()):
            if target not in indices:
                yield from strongconnect(target)
                low_links[node] = min(low_links[node], low_links[target])
            elif target in on_stack:
                low_links[node] = min(low_links[node], indices[target])

        if low_links[node] != indices[node]:
            return

        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1:
            yield frozenset(component)

    for node in sorted(edges):
        if node not in indices:
            yield from strongconnect(node)


def test_runtime_import_graph_has_no_forbidden_sccs() -> None:
    """Runtime import SCC scan must stay clear of confirmed intra-layer cycles."""
    edges = _build_runtime_import_graph()
    actual_sccs = tuple(_iter_runtime_sccs(edges))
    blocked = [
        sorted(component)
        for component in actual_sccs
        if component in FORBIDDEN_RUNTIME_SCCS
    ]
    assert not blocked, (
        "Runtime import SCC scan found forbidden strongly connected components "
        "(TYPE_CHECKING imports are ignored):\n"
        + "\n".join(f"- {', '.join(component)}" for component in blocked)
    )
