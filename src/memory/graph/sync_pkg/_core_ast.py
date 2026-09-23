"""AST probes extracted from the graph sync kernel (AUD-002 slice: ast_probes)."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from memory.graph.sync_pkg._core_convert import (
    _is_dataframe_model_base,
    _is_protocol_base,
    _read_text,
)
from memory.graph.sync_pkg._core_models import _ShapeNormalizer

__all__ = [
    "_CONTROL_FLOW_NODES",
    "_base_name",
    "_callable_ast_node_count",
    "_callable_branch_count",
    "_callable_call_count",
    "_callable_helper_call_count",
    "_callable_max_nesting_depth",
    "_dataframe_model_class_names",
    "_imported_repo_modules",
    "_imported_symbols",
    "_looks_like_dataframe_model_class",
    "_matching_imported_module_names",
    "_normalized_callable_hash",
    "_parse_python_ast",
    "_protocol_class_names",
    "_signature_hash",
]

_CONTROL_FLOW_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.Match,
    ast.IfExp,
    ast.With,
    ast.AsyncWith,
)


def _parse_python_ast(path: Path) -> ast.Module | None:
    if path.suffix != ".py":
        return None
    try:
        return ast.parse(_read_text(path), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    return ""


def _signature_hash(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    payload = {
        "async": isinstance(node, ast.AsyncFunctionDef),
        "posonly": len(args.posonlyargs),
        "args": len(args.args),
        "kwonly": len(args.kwonlyargs),
        "vararg": args.vararg is not None,
        "kwarg": args.kwarg is not None,
        "decorator_count": len(node.decorator_list),
    }
    encoded = json.dumps(payload, sort_keys=True)
    # Deterministic structural fingerprint used for clustering, not for secrets.
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalized_callable_hash(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    module = ast.Module(body=node.body, type_ignores=[])
    normalized = _ShapeNormalizer().visit(module)
    ast.fix_missing_locations(normalized)
    dumped = ast.dump(normalized, annotate_fields=True, include_attributes=False)
    # Deterministic structural fingerprint used for clustering, not for secrets.
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _callable_ast_node_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return sum(1 for _ in ast.walk(node))


def _callable_branch_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    count = 0
    for child in ast.walk(node):
        if isinstance(child, _CONTROL_FLOW_NODES):
            count += 1
        elif isinstance(child, ast.BoolOp):
            count += max(0, len(child.values) - 1)
        elif isinstance(child, ast.comprehension):
            count += len(child.ifs)
    return count


def _callable_max_nesting_depth(node: ast.AST) -> int:
    def visit(current: ast.AST, depth: int) -> int:
        max_depth = depth
        for child in ast.iter_child_nodes(current):
            next_depth = depth + 1 if isinstance(child, _CONTROL_FLOW_NODES) else depth
            max_depth = max(max_depth, visit(child, next_depth))
        return max_depth

    return visit(node, 0)


def _callable_call_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return sum(1 for child in ast.walk(node) if isinstance(child, ast.Call))


def _callable_helper_call_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    tokens = ("_", "helper", "policy", "codec", "mixin", "fsm", "compat")
    count = 0
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func_name = _base_name(child.func).casefold()
        if func_name and any(token in func_name for token in tokens):
            count += 1
    return count


def _protocol_class_names(path: Path) -> list[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return []

    protocol_names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if any(_is_protocol_base(base) for base in node.bases):
            protocol_names.append(node.name)
    return protocol_names


def _dataframe_model_class_names(path: Path) -> list[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return []

    class_names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if _looks_like_dataframe_model_class(node):
            class_names.append(node.name)
    return class_names


def _looks_like_dataframe_model_class(node: ast.ClassDef) -> bool:
    """Return True when a class likely represents a Pandera DataFrameModel schema."""
    if any(_is_dataframe_model_base(base) for base in node.bases):
        return True
    if not node.name.endswith("Schema"):
        return False
    return any(isinstance(child, ast.AnnAssign) for child in node.body)


def _imported_symbols(path: Path) -> list[tuple[str, str, str]]:
    tree = _parse_python_ast(path)
    if tree is None:
        return []

    imports: list[tuple[str, str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        for alias in node.names:
            imports.append((node.module, alias.name, alias.asname or alias.name))
    return imports


def _matching_imported_module_names(
    node: ast.AST, prefixes: tuple[str, ...]
) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(
            alias.name for alias in node.names if alias.name.startswith(prefixes)
        )
    if (
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith(prefixes)
    ):
        return (node.module,)
    return ()


def _imported_repo_modules(path: Path, prefixes: tuple[str, ...]) -> set[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        imported.update(_matching_imported_module_names(node, prefixes))
    return imported
