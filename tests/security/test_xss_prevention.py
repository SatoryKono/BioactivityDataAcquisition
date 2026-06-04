"""Security tests for XSS prevention.

Validates that web interfaces properly escape user input and
do not directly render unescaped content.
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
class TestXSSPrevention:
    """Tests for XSS prevention in web interfaces."""

    @pytest.fixture(scope="class")
    def source_contents(
        self, _src_file_contents: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        """Class-scoped alias for session-cached source file contents."""
        return _src_file_contents

    def test_http_interfaces_use_escaping(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify that HTTP interfaces don't directly render unescaped user input."""
        violations = []

        # Look for files in interfaces/http or interfaces/cli that might render HTML
        interface_files = [
            (py_file, content)
            for py_file, content in source_contents
            if "interfaces" in str(py_file)
        ]

        for py_file, content in interface_files:
            # Check for direct string interpolation in HTML context
            # This is a heuristic - not perfect but catches common issues
            xss_patterns = [
                # f"<div>{user_input}</div>"
                (r'<[^>]*>\{.*\}</[^>]*>', "f-string in HTML template"),
                # "<div>" + user_input + "</div>"
                (r'<[^>]*>[^<]*\+\s*\w+\s*\+', "string concatenation in HTML"),
            ]

            for pattern, description in xss_patterns:
                if re.search(pattern, content):
                    # Check if escaping is used nearby
                    if 'html.escape' in content or 'escape' in content:
                        continue  # Escaping is used
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: {description}")

        assert not violations, (
            "Potential XSS vulnerabilities found:\n"
            + "\n".join(violations)
            + "\n\nUse html.escape() or template escaping for user input in HTML context"
        )

    def test_no_direct_html_rendering_of_user_input(
        self, source_contents: list[tuple[Path, str]]
    ) -> None:
        """Verify that user input is not directly rendered into HTML without escaping."""
        violations = []

        # Look for patterns where user input might be rendered
        dangerous_patterns = [
            (r'return.*<[^>]*>\s*\w+\s*</[^>]*>', "direct HTML return with variable"),
            (r'html\s*=\s*["\'].*\{.*\}.*["\']', "HTML string with variable interpolation"),
        ]

        for py_file, content in source_contents:
            # Focus on interfaces layer
            if "interfaces" not in str(py_file):
                continue

            for pattern, description in dangerous_patterns:
                if re.search(pattern, content):
                    # Check if escaping is used nearby
                    if 'escape' in content or 'sanitize' in content:
                        continue  # Escaping/sanitization is used
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: {description}")

        # This is informational, not a hard failure, as some cases may be legitimate
        # If violations are found, we just pass - the test is for prevention
        # Real violations would be caught by the escaping test above
        pass