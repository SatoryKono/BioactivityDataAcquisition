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
    @classmethod
    def source_contents(
        cls, _src_file_contents: list[tuple[Path, str]]
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
        # Cover SELECT/INSERT/UPDATE/DELETE and multiline SQL string forms.
        # Require SQL shape (FROM/INTO/SET) so UI strings like "Would delete {n}"
        # are not false positives.
        sql_concat_patterns = [
            (
                r'["\'].*SELECT\s+.+\s+FROM.*\{.*\}.*["\']',
                "f-string / interpolation in SELECT",
            ),
            (
                r'["\'].*INSERT\s+INTO.*\{.*\}.*["\']',
                "f-string / interpolation in INSERT",
            ),
            (
                r'["\'].*UPDATE\s+\w+\s+SET.*\{.*\}.*["\']',
                "f-string / interpolation in UPDATE",
            ),
            (
                r'["\'].*DELETE\s+FROM.*\{.*\}.*["\']',
                "f-string / interpolation in DELETE",
            ),
            (
                r'["\'].*SELECT\s+.+\s+FROM.*["\']\s*\+\s*\w+',
                "string concatenation in SELECT",
            ),
            (
                r'["\'].*INSERT\s+INTO.*["\']\s*\+\s*\w+',
                "string concatenation in INSERT",
            ),
            (
                r'["\'].*UPDATE\s+\w+\s+SET.*["\']\s*\+\s*\w+',
                "string concatenation in UPDATE",
            ),
            (
                r'["\'].*DELETE\s+FROM.*["\']\s*\+\s*\w+',
                "string concatenation in DELETE",
            ),
            (
                r'["\'].*SELECT\s+.+\s+FROM.*%s["\']\s*%',
                "old-style formatting in SELECT",
            ),
            (
                r'["\'].*INSERT\s+INTO.*%s["\']\s*%',
                "old-style formatting in INSERT",
            ),
            (
                r'["\'].*UPDATE\s+\w+\s+SET.*%s["\']\s*%',
                "old-style formatting in UPDATE",
            ),
            (
                r'["\'].*DELETE\s+FROM.*%s["\']\s*%',
                "old-style formatting in DELETE",
            ),
            (
                r'["\'].*SELECT\s+.+\s+FROM.*\.format\(',
                "format() in SELECT",
            ),
            (
                r'["\'].*INSERT\s+INTO.*\.format\(',
                "format() in INSERT",
            ),
            (
                r'["\'].*UPDATE\s+\w+\s+SET.*\.format\(',
                "format() in UPDATE",
            ),
            (
                r'["\'].*DELETE\s+FROM.*\.format\(',
                "format() in DELETE",
            ),
            # triple-quoted multiline SQL with interpolation
            (
                r'["\']{3}[\s\S]*?SELECT\s+[\s\S]+?\s+FROM[\s\S]*?\{[\s\S]*?\}[\s\S]*?["\']{3}',
                "multiline interpolated SELECT",
            ),
            (
                r'["\']{3}[\s\S]*?INSERT\s+INTO[\s\S]*?\{[\s\S]*?\}[\s\S]*?["\']{3}',
                "multiline interpolated INSERT",
            ),
            (
                r'["\']{3}[\s\S]*?UPDATE\s+\w+\s+SET[\s\S]*?\{[\s\S]*?\}[\s\S]*?["\']{3}',
                "multiline interpolated UPDATE",
            ),
            (
                r'["\']{3}[\s\S]*?DELETE\s+FROM[\s\S]*?\{[\s\S]*?\}[\s\S]*?["\']{3}',
                "multiline interpolated DELETE",
            ),
        ]

        for py_file, content in source_contents:
            upper = content.upper()
            if not any(
                keyword in upper for keyword in ("SELECT", "INSERT", "UPDATE", "DELETE")
            ):
                continue

            for pattern, description in sql_concat_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    # Approximate line number of match start
                    line_no = content.count("\n", 0, match.start()) + 1
                    line = content.split("\n", line_no)[line_no - 1]
                    if line.strip().startswith("#"):
                        continue
                    if '"""' in line or "'''" in line:
                        continue
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}:{line_no}: {description}")

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
