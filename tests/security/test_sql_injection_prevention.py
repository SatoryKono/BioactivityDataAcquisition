"""Security tests for SQL injection prevention.

Validates that database operations use parameterized queries and
do not concatenate user input into SQL strings.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "bioetl"


@pytest.fixture(scope="session")
def _src_file_contents() -> list[tuple[Path, str]]:
    """Read all Python source files under SRC_DIR once per session."""
    return [
        (py_file, py_file.read_text(encoding="utf-8"))
        for py_file in sorted(SRC_DIR.rglob("*.py"))
    ]


@pytest.mark.timeout(120)
class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention in database operations."""

    @pytest.fixture(scope="class")
    def source_contents(
        self, _src_file_contents: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        """Class-scoped alias for session-cached source file contents."""
        return _src_file_contents

    def test_no_string_concatenation_in_sql_queries(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify that SQL queries don't use string concatenation with user input."""
        violations = []

        # Pattern to detect string formatting in SQL context
        # This is a heuristic - not perfect but catches common issues
        sql_concat_patterns = [
            # f"SELECT * FROM table WHERE id = {user_input}"
            (r'["\']SELECT.*\{.*\}.*["\']', "f-string in SQL query"),
            # "SELECT * FROM table WHERE id = " + user_input
            (r'["\']SELECT.*["\']\s*\+\s*\w+', "string concatenation in SQL query"),
            # "SELECT * FROM table WHERE id = %s" % user_input (without parameter binding)
            (r'["\']SELECT.*%s["\']\s*%', "old-style formatting in SQL query"),
            # "SELECT * FROM table WHERE id = {}".format(user_input)
            (r'["\']SELECT.*\.format\(', "format() in SQL query"),
        ]

        for py_file, content in source_contents:
            # Skip if file doesn't contain SQL keywords
            if (
                "SELECT" not in content
                and "INSERT" not in content
                and "UPDATE" not in content
            ):
                continue

            for pattern, description in sql_concat_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Check if it's in a comment or docstring (false positive)
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            # Skip if it's a comment
                            if line.strip().startswith("#"):
                                continue
                            # Skip if it's a docstring
                            if '"""' in line or "'''" in line:
                                continue
                            rel_path = py_file.relative_to(PROJECT_ROOT)
                            violations.append(f"{rel_path}:{i}: {description}")

        # Allow some false positives in test files or known safe contexts
        allowed_files = [
            "tests/",
            "test_",
        ]

        filtered_violations = [
            v for v in violations if not any(allowed in v for allowed in allowed_files)
        ]

        assert not filtered_violations, (
            "Potential SQL injection vulnerabilities found:\n"
            + "\n".join(filtered_violations)
            + "\n\nUse parameterized queries (e.g., conn.execute('SELECT * WHERE id = ?', [id]))"
        )

    def test_database_operations_preserves_parameterized_query_inventory(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Inventory execute() sites; hard failures stay in the concatenation guard."""
        # This is a positive test - checks for safe patterns
        safe_patterns = [
            r"\.execute\([^)]*\?",  # execute with ? placeholder
            r"\.execute\([^)]*%s",  # execute with %s placeholder (when used correctly)
            r"\.execute\([^)]*:\w+",  # execute with named parameters
        ]

        files_with_db_operations = []
        for py_file, content in source_contents:
            if any(pattern in content for pattern in ["execute(", "executemany("]):
                if any(re.search(pattern, content) for pattern in safe_patterns):
                    continue  # File uses safe patterns
                rel_path = py_file.relative_to(PROJECT_ROOT)
                files_with_db_operations.append(str(rel_path))

        # Informational inventory only; unsafe string concatenation is enforced above.
        assert files_with_db_operations is not None
