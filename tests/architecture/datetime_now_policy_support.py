# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shared helpers for datetime.now()/utcnow() architecture policy tests."""

from __future__ import annotations

import ast
from pathlib import Path
from collections.abc import Callable


def collect_datetime_now_calls(
    py_file: Path,
    *,
    relative_path: str,
    tolerate_syntax_error: bool = False,
) -> list[str]:
    """Collect datetime.now()/utcnow() calls for one Python file."""
    source = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        if tolerate_syntax_error:
            return []
        raise

    calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in ("now", "utcnow"):
            continue

        if isinstance(node.func.value, ast.Name) and node.func.value.id == "datetime":
            calls.append(f"{relative_path}:{node.lineno}: datetime.{node.func.attr}()")
        elif (
            isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "datetime"
        ):
            calls.append(
                f"{relative_path}:{node.lineno}: datetime.datetime.{node.func.attr}()"
            )
    return calls


def collect_datetime_policy_violations(
    *,
    py_files: list[Path],
    allowed_paths: set[str],
    relative_path_fn: Callable[[Path], str],
    tolerate_syntax_error: bool = False,
) -> list[str]:
    """Collect all datetime.now()/utcnow() violations outside the allowlist."""
    violations: list[str] = []
    for py_file in py_files:
        relative_path = relative_path_fn(py_file)
        if relative_path in allowed_paths:
            continue
        violations.extend(
            collect_datetime_now_calls(
                py_file,
                relative_path=relative_path,
                tolerate_syntax_error=tolerate_syntax_error,
            )
        )
    return violations


def assert_allowed_paths_exist(
    *,
    py_files: list[Path],
    allowed_paths: set[str],
    relative_path_fn: Callable[[Path], str],
) -> None:
    """Verify allowlisted relative paths still exist."""
    existing_paths = {relative_path_fn(py_file) for py_file in py_files}
    missing = allowed_paths - existing_paths
    assert not missing, (
        f"ALLOWED_PATHS contains non-existent files: {sorted(missing)}. "
        "Remove stale entries from the allowed list."
    )


def assert_allowed_paths_are_basename_unique(
    *,
    py_files: list[Path],
    allowed_paths: set[str],
    relative_path_fn: Callable[[Path], str],
    message_prefix: str,
) -> None:
    """Verify path-based exceptions do not silently widen by basename reuse."""
    existing_paths = {relative_path_fn(py_file) for py_file in py_files}
    basename_to_paths: dict[str, list[str]] = {}
    for path_str in existing_paths:
        basename_to_paths.setdefault(Path(path_str).name, []).append(path_str)

    ambiguous = {
        allowed_path: sorted(basename_to_paths[Path(allowed_path).name])
        for allowed_path in allowed_paths
        if len(basename_to_paths.get(Path(allowed_path).name, [])) > 1
    }
    assert not ambiguous, message_prefix + f"{ambiguous}"


def find_stale_datetime_exemptions(
    *,
    py_files: list[Path],
    allowed_paths: set[str],
    relative_path_fn: Callable[[Path], str],
    tolerate_syntax_error: bool = False,
) -> list[str]:
    """Return allowlisted paths that no longer need a datetime exception."""
    file_by_path = {relative_path_fn(py_file): py_file for py_file in py_files}
    return [
        allowed_path
        for allowed_path in sorted(allowed_paths)
        if allowed_path in file_by_path
        and not collect_datetime_now_calls(
            file_by_path[allowed_path],
            relative_path=allowed_path,
            tolerate_syntax_error=tolerate_syntax_error,
        )
    ]
