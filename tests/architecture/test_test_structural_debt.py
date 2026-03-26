"""Architecture guardrails for structural debt in test suite."""

from __future__ import annotations

import ast
from pathlib import Path

MAX_TEST_FILE_LOC = 2000
MAX_TEST_FUNCTION_LOC = 200


def test_no_test_files_over_2000_loc(test_content_cache: dict[Path, str]) -> None:
    """Keep test file size under 2000 LOC for readability and maintainability."""
    violations: list[tuple[int, Path]] = []

    for test_file, content in test_content_cache.items():
        loc = len(content.splitlines())
        if loc > MAX_TEST_FILE_LOC:
            violations.append((loc, test_file))

    violations.sort(reverse=True)
    assert not violations, (
        f"Found {len(violations)} test files above {MAX_TEST_FILE_LOC} LOC:\n"
        + "\n".join(f"  - {path}: {loc} LOC" for loc, path in violations[:30])
    )


def test_no_test_functions_over_200_loc(test_ast_cache: dict[Path, ast.Module]) -> None:
    """Keep individual test function bodies under 200 LOC."""
    violations: list[tuple[int, Path, str, int]] = []

    for test_file, tree in test_ast_cache.items():
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test"):
                continue

            start = node.lineno
            end = node.end_lineno or start
            length = end - start + 1
            if length > MAX_TEST_FUNCTION_LOC:
                violations.append((length, test_file, node.name, start))

    violations.sort(reverse=True)
    assert not violations, (
        f"Found {len(violations)} test functions above {MAX_TEST_FUNCTION_LOC} LOC:\n"
        + "\n".join(
            f"  - {path}:{line} {name}(): {length} LOC"
            for length, path, name, line in violations[:30]
        )
    )
