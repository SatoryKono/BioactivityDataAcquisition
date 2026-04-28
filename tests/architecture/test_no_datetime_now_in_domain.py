"""Architecture test: current time creation is restricted in the domain layer.

REQ-ARCH-031: Single source of truth for timestamps.
Domain business paths must receive timestamps explicitly instead of creating
them implicitly at read/transition time.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.datetime_now_policy_support import (
    assert_allowed_paths_are_basename_unique,
    assert_allowed_paths_exist,
    collect_datetime_now_calls,
    collect_datetime_policy_violations,
    find_stale_datetime_exemptions,
)

DOMAIN_DIR = Path("src/bioetl/domain")

# Only the canonical pipeline context seam may create the current time internally.
ALLOWED_PATHS: set[str] = {
    "context.py",
}


def _domain_base() -> Path:
    """Resolve domain base path from either repo root or tests cwd."""
    if DOMAIN_DIR.exists():
        return DOMAIN_DIR
    return Path(__file__).parent.parent.parent / DOMAIN_DIR


def _relative_domain_path(py_file: Path) -> str:
    """Return repo-stable domain-relative path using POSIX separators."""
    return py_file.relative_to(_domain_base()).as_posix()


def _datetime_now_calls(py_file: Path) -> list[str]:
    """Collect datetime.now()/utcnow() calls for a Python file."""
    return collect_datetime_now_calls(
        py_file,
        relative_path=_relative_domain_path(py_file),
    )


class TestNoDatetimeNowInDomain:
    """Tests ensuring domain business paths don't create implicit timestamps."""

    @pytest.fixture
    def domain_python_files(self) -> list[Path]:
        """Get all Python files in domain directory."""
        base = _domain_base()
        return list(base.rglob("*.py"))

    def test_no_datetime_now_in_domain(self, domain_python_files: list[Path]) -> None:
        """Domain MUST NOT call datetime.now() outside sanctioned seams."""
        violations = collect_datetime_policy_violations(
            py_files=domain_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_domain_path,
        )

        assert not violations, (
            "datetime.now()/utcnow() found in domain layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nDomain business paths should receive timestamps explicitly. "
            "Only the canonical PipelineContext time-source seam may create the "
            "current time inside domain/context.py. See ADR-014."
        )

    def test_allowed_paths_still_exist_and_are_unambiguous(
        self, domain_python_files: list[Path]
    ) -> None:
        """Verify path-based domain exceptions remain explicit and basename-unique."""
        assert_allowed_paths_exist(
            py_files=domain_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_domain_path,
        )
        assert_allowed_paths_are_basename_unique(
            py_files=domain_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_domain_path,
            message_prefix=(
                "ALLOWED_PATHS must stay basename-unique to prevent silent widening "
                "of domain datetime exceptions: "
            ),
        )

    def test_allowed_paths_still_require_exception(
        self, domain_python_files: list[Path]
    ) -> None:
        """Force removal of allowlist entries once datetime usage is refactored away."""
        stale_exemptions = find_stale_datetime_exemptions(
            py_files=domain_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_domain_path,
        )

        assert not stale_exemptions, (
            "Remove stale domain datetime exceptions that no longer need allowlisting: "
            f"{stale_exemptions}"
        )
