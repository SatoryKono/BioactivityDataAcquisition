"""Shared inventory helpers with a single runtime owner."""

from __future__ import annotations

import ast
from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_shared import (
    _EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS,
)

REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {}


def _module_path_from_import(module_name: str, repo_root: Path) -> Path | None:
    if not module_name.startswith("bioetl."):
        return None
    module_rel = module_name.replace(".", "/")
    module_path = repo_root / "src" / f"{module_rel}.py"
    if module_path.exists():
        return module_path
    package_init = repo_root / "src" / module_rel / "__init__.py"
    if package_init.exists():
        return package_init
    return None


def _collect_module_string_bindings(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
    except (UnicodeDecodeError, OSError, TimeoutError):
        return {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    bindings: dict[str, str] = {}
    for node in tree.body:
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value_node.value
    return bindings


def _iter_string_assignments(tree: ast.AST) -> list[tuple[list[ast.expr], str]]:
    assignments: list[tuple[list[ast.expr], str]] = []
    for node in ast.walk(tree):
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        assignments.append((targets, value_node.value))
    return assignments


def _resolve_imported_string_bindings(
    tree: ast.AST,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]] | None = None,
) -> dict[str, str]:
    resolved_cache = cache if cache is not None else {}
    bindings: dict[str, str] = {}
    for node in _import_from_nodes(tree):
        relevant_aliases = _imported_string_constant_aliases(node.names)
        if not relevant_aliases:
            continue
        module_bindings = _module_string_bindings(
            node.module,
            repo_root=repo_root,
            cache=resolved_cache,
        )
        if module_bindings is None:
            continue
        _merge_imported_string_aliases(bindings, module_bindings, relevant_aliases)
    return bindings


def _collect_class_attribute_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for class_node in _class_nodes(tree):
        bindings.update(_class_attribute_string_bindings(class_node))
    return bindings


def _collect_repo_class_attribute_bindings(
    candidate_files: list[tuple[Path, str]],
) -> dict[str, str]:
    """Collect string-valued class attributes across runtime scan roots.

    This lets helper modules resolve ``self.METRIC_*`` style references even when
    the concrete string constant is declared on a subclass in another file.
    """
    bindings: dict[str, str] = {}
    for _path, text in candidate_files:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        bindings.update(_collect_class_attribute_bindings(tree))
    return bindings


def _resolve_metric_name_expr(
    node: ast.expr,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return string_bindings.get(node.id) or metric_bindings.get(node.id)
    if isinstance(node, ast.Attribute):
        return attribute_bindings.get(node.attr) or metric_bindings.get(node.attr)
    return None


def _collect_local_string_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for targets, value in _iter_string_assignments(tree):
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value
    return bindings


def _call_method_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _import_from_nodes(tree: ast.AST) -> list[ast.ImportFrom]:
    """Return import-from nodes with concrete module names."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]


def _looks_like_imported_string_constant_name(name: str) -> bool:
    """Return whether an imported name looks like a UPPER_SNAKE_CASE constant."""
    return any(ch.isalpha() for ch in name) and name.upper() == name


def _imported_string_constant_aliases(aliases: list[ast.alias]) -> list[ast.alias]:
    """Keep only aliases worth resolving as imported string constants."""
    return [
        alias
        for alias in aliases
        if alias.name != "*" and _looks_like_imported_string_constant_name(alias.name)
    ]


def _module_string_bindings(
    module_name: str | None,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]],
) -> dict[str, str] | None:
    """Load cached string bindings for one imported module."""
    if module_name is None:
        return None
    module_path = _module_path_from_import(module_name, repo_root)
    if module_path is None:
        return None
    if module_path not in cache:
        try:
            cache[module_path] = _collect_module_string_bindings(module_path)
        except (UnicodeDecodeError, OSError, TimeoutError):
            cache[module_path] = {}
    return cache[module_path]


def _merge_imported_string_aliases(
    bindings: dict[str, str],
    module_bindings: dict[str, str],
    aliases: list[ast.alias],
) -> None:
    """Merge imported string constants into the local binding map."""
    for alias in aliases:
        if alias.name == "*":
            continue
        resolved = module_bindings.get(alias.name)
        if resolved is not None:
            bindings[alias.asname or alias.name] = resolved


def _class_nodes(tree: ast.AST) -> list[ast.ClassDef]:
    """Return all class definitions in the tree."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _class_attribute_string_bindings(class_node: ast.ClassDef) -> dict[str, str]:
    """Collect string-valued class attribute bindings for one class."""
    bindings: dict[str, str] = {}
    for body_node in class_node.body:
        for targets, value in _iter_string_assignments(body_node):
            for target in targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = value
    return bindings


def _call_nodes(tree: ast.AST) -> list[ast.Call]:
    """Return all call nodes from the AST."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]


def _resolve_imported_metric_bindings(tree: ast.AST) -> dict[str, str]:
    bindings = dict(_EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS)
    for node in _import_from_nodes(tree):
        for alias in node.names:
            if alias.name == "*":
                continue
            metric_name = _EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS.get(alias.name)
            if metric_name is not None:
                bindings[alias.asname or alias.name] = metric_name
    return bindings
