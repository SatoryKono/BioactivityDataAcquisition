"""Identify Python execution calls without mistaking Polars expressions for eval."""

from __future__ import annotations

import ast


def execution_calls(source: str) -> tuple[str, ...]:
    """Find direct, qualified and imported execution builtins in parsed source."""
    tree = ast.parse(source)
    aliases = {"eval": "eval", "exec": "exec", "compile": "compile"}
    polars_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            polars_names.update(
                item.asname or item.name for item in node.names if item.name == "polars"
            )
        if isinstance(node, ast.ImportFrom) and node.module == "builtins":
            aliases.update({item.asname or item.name: item.name for item in node.names})
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = aliases.get(func.id, "") if isinstance(func, ast.Name) else ""
        if isinstance(func, ast.Attribute):
            name = func.attr
            # Polars ListNameSpace.eval evaluates a column expression, not Python.
            if name == "eval" and _polars_list_eval(func, polars_names):
                continue
        if name in {"eval", "exec"}:
            violations.append(f"{name}() at line {node.lineno}")
        elif name == "compile" and _exec_mode(node):
            violations.append(f"compile() with exec mode at line {node.lineno}")
    return tuple(violations)


def _polars_list_eval(func: ast.Attribute, polars_names: set[str]) -> bool:
    owner = func.value
    if not isinstance(owner, ast.Attribute) or owner.attr != "list":
        return False
    expression = owner.value
    if not isinstance(expression, ast.Call) or not isinstance(
        expression.func, ast.Attribute
    ):
        return False
    namespace = expression.func.value
    return (
        isinstance(namespace, ast.Name)
        and namespace.id in polars_names
        and expression.func.attr == "col"
    )


def _exec_mode(call: ast.Call) -> bool:
    mode = call.args[2] if len(call.args) >= 3 else None
    mode = next((item.value for item in call.keywords if item.arg == "mode"), mode)
    return isinstance(mode, ast.Constant) and mode.value == "exec"
