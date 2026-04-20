"""Architecture guardrails for structural debt in test suite."""

from __future__ import annotations

import ast
from pathlib import Path

MAX_TEST_FILE_LOC = 2000
MAX_TEST_FUNCTION_LOC = 200

TEST_FILE_LOC_EXEMPTIONS = {
    "tests/unit/scripts/ops/test_neo4j_memory_sync.py": 3026,
    "tests/unit/infrastructure/storage/test_bronze_writer.py": 2016,
}

TEST_FUNCTION_LOC_EXEMPTIONS = {
    "tests/unit/scripts/ops/test_neo4j_memory_sync.py::test_snapshot_contains_core_repo_surfaces": 316,
    "tests/unit/domain/ports/test_protocol_contract_examples.py::test_write_silver_signature": 204,
}


def test_no_test_files_over_2000_loc(test_content_cache: dict[Path, str]) -> None:
    """Keep test file size under 2000 LOC for readability and maintainability."""
    violations: list[tuple[int, Path]] = []

    for test_file, content in test_content_cache.items():
        loc = len(content.splitlines())
        rel_path = test_file.relative_to(Path.cwd()).as_posix()
        file_limit = TEST_FILE_LOC_EXEMPTIONS.get(rel_path, MAX_TEST_FILE_LOC)
        if loc > file_limit:
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
            rel_path = test_file.relative_to(Path.cwd()).as_posix()
            function_key = f"{rel_path}::{node.name}"
            function_limit = TEST_FUNCTION_LOC_EXEMPTIONS.get(
                function_key, MAX_TEST_FUNCTION_LOC
            )
            if length > function_limit:
                violations.append((length, test_file, node.name, start))

    violations.sort(reverse=True)
    assert not violations, (
        f"Found {len(violations)} test functions above {MAX_TEST_FUNCTION_LOC} LOC:\n"
        + "\n".join(
            f"  - {path}:{line} {name}(): {length} LOC"
            for length, path, name, line in violations[:30]
        )
    )
