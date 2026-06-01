"""Architecture test: no new datetime.now() / datetime.now(UTC) in test code.

This is the test-side counterpart of test_no_datetime_now_in_infrastructure.py.
Tests should use deterministic timestamps via ``tests.helpers.clock.FixedClock``
or ``tests.helpers.clock.StepClock`` (or plain ``datetime(...)`` constants)
instead of calling ``datetime.now()``.

The ALLOWED_PATHS set acts as a ratchet: every file listed here is a known
legacy consumer.  The set should only shrink over time — new test files must
NOT be added.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.datetime_now_policy_support import (
    assert_allowed_paths_exist,
    collect_datetime_now_calls,
    collect_datetime_policy_violations,
    find_stale_datetime_exemptions,
)

pytestmark = pytest.mark.architecture

TESTS_DIR = Path("tests")

# Paths relative to ``tests/`` that are allowed to use datetime.now().
# This allowlist should shrink over time as files are migrated to FixedClock /
# StepClock or fixed datetime constants.
ALLOWED_PATHS: set[str] = set()


def _tests_base() -> Path:
    """Resolve tests base path from either repo root or tests cwd."""
    if TESTS_DIR.exists():
        return TESTS_DIR
    return Path(__file__).parent.parent


def _relative_test_path(py_file: Path) -> str:
    """Return tests-relative POSIX path for stable allowlist matching."""
    return py_file.relative_to(_tests_base()).as_posix()


def _datetime_now_calls(py_file: Path) -> list[str]:
    """Collect datetime.now()/utcnow() calls for a Python file."""
    return collect_datetime_now_calls(
        py_file,
        relative_path=_relative_test_path(py_file),
        tolerate_syntax_error=True,
    )


class TestNoDatetimeNowInTests:
    """Tests ensuring test code uses deterministic timestamps."""

    @pytest.fixture
    def test_python_files(self) -> list[Path]:
        """Get all Python files under tests/, excluding architecture tests."""
        base = _tests_base()
        arch = base / "architecture"
        return [
            py_file
            for py_file in sorted(base.rglob("*.py"))
            if not py_file.is_relative_to(arch)
        ]

    def test_no_datetime_now_in_tests(self, test_python_files: list[Path]) -> None:
        """Test code MUST NOT introduce new datetime.now() / datetime.now(UTC) calls.

        Use ``tests.helpers.clock.FixedClock`` or ``tests.helpers.clock.StepClock``
        for deterministic timestamps, or plain ``datetime(2025, 1, 1, ...)`` constants.
        """
        violations = collect_datetime_policy_violations(
            py_files=test_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_test_path,
            tolerate_syntax_error=True,
        )

        assert not violations, (
            "datetime.now()/utcnow() found in test code:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse tests.helpers.clock.FixedClock / StepClock or fixed "
            "datetime constants instead. See tests/helpers/clock.py."
        )

    def test_allowed_paths_still_exist(self, test_python_files: list[Path]) -> None:
        """Verify allowlisted paths still exist — remove stale entries."""
        assert_allowed_paths_exist(
            py_files=test_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_test_path,
        )

    def test_in_no_datetime_now_in__require_exception__1f79c9d6(
        self, test_python_files: list[Path]
    ) -> None:
        """Force removal of allowlist entries once datetime usage is refactored away."""
        stale_exemptions = find_stale_datetime_exemptions(
            py_files=test_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_test_path,
            tolerate_syntax_error=True,
        )

        assert not stale_exemptions, (
            "Remove stale datetime exceptions that no longer need allowlisting: "
            f"{stale_exemptions}"
        )
