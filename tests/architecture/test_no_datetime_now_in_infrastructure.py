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
"""Architecture test: datetime.now()/utcnow() only in application/composition layers.

REQ-ARCH-001: Single source of truth for timestamps.
Timestamps should be created in application layer and passed down.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md

Note: datetime.utcnow() is deprecated in Python 3.12+ (PEP 692).
Use datetime.now(UTC) instead for timezone-aware UTC timestamps.
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

pytestmark = pytest.mark.architecture

# Path relative to project root
INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")

# Files allowed to use datetime.now() - with justification.
# Full documentation in ADR-014: docs/02-architecture/decisions/ADR-014-deterministic-writes.md
#
# Criteria for exceptions:
# 1. Timestamp does not affect determinism of batch operations
# 2. Timestamp is required for real-time monitoring/operations
# 3. Timestamp is not used in Bronze/Silver/Gold data
#
# Path-based allowlist only. Basename matching can silently widen exemptions
# when the same filename exists in multiple infrastructure subpackages.
ALLOWED_PATHS: set[str] = set()


def _infrastructure_base() -> Path:
    """Resolve infrastructure base path from either repo root or tests cwd."""
    if INFRASTRUCTURE_DIR.exists():
        return INFRASTRUCTURE_DIR
    return Path(__file__).parent.parent.parent / INFRASTRUCTURE_DIR


def _relative_infrastructure_path(py_file: Path) -> str:
    """Return repo-stable infrastructure-relative path using POSIX separators."""
    return py_file.relative_to(_infrastructure_base()).as_posix()


def _datetime_now_calls(py_file: Path) -> list[str]:
    """Collect datetime.now()/utcnow() calls for a Python file."""
    return collect_datetime_now_calls(
        py_file,
        relative_path=_relative_infrastructure_path(py_file),
    )


class TestNoDatetimeNowInInfrastructure:
    """Tests ensuring infrastructure layer doesn't create timestamps."""

    @pytest.fixture
    def infrastructure_python_files(self) -> list[Path]:
        """Get all Python files in infrastructure directory."""
        base = _infrastructure_base()
        return list(base.rglob("*.py"))

    def test_no_datetime_now_in_infrastructure(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Infrastructure MUST NOT call datetime.now() or datetime.utcnow() directly.

        Timestamps should be created in application layer (e.g., PipelineContext)
        and passed as parameters to infrastructure components.

        Note: datetime.utcnow() is deprecated in Python 3.12+ (PEP 692).
        """
        violations = collect_datetime_policy_violations(
            py_files=infrastructure_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_infrastructure_path,
        )

        assert not violations, (
            "datetime.now()/utcnow() found in infrastructure layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nTimestamps should be created in application layer "
            "(e.g., PipelineContext.started_at) and passed as parameters. "
            "See ADR-014."
        )

    def test_datetime_now_in_tests_no_datetime_now_in_94__5391b5b4(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Verify that path-based exceptions still exist and avoid basename drift.

        This prevents stale exceptions from accumulating and blocks future
        reintroduction of ambiguous basename-based exemptions like `client.py`.
        """
        assert_allowed_paths_exist(
            py_files=infrastructure_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_infrastructure_path,
        )
        assert_allowed_paths_are_basename_unique(
            py_files=infrastructure_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_infrastructure_path,
            message_prefix=(
                "ALLOWED_PATHS must stay basename-unique to prevent silent widening "
                "of datetime exceptions: "
            ),
        )

    def test_now_in_infrastructure__require_exception__ba8fc9ec(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Force removal of allowlist entries once datetime usage is refactored away."""
        stale_exemptions = find_stale_datetime_exemptions(
            py_files=infrastructure_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_infrastructure_path,
        )

        assert not stale_exemptions, (
            "Remove stale datetime exceptions that no longer need allowlisting: "
            f"{stale_exemptions}"
        )
