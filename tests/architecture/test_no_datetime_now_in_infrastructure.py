"""Architecture test: datetime.now()/utcnow() only in application/composition layers.

REQ-ARCH-031: Single source of truth for timestamps.
Timestamps should be created in application layer and passed down.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md

Note: datetime.utcnow() is deprecated in Python 3.12+ (PEP 692).
Use datetime.now(UTC) instead for timezone-aware UTC timestamps.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

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
ALLOWED_PATHS: set[str] = {
    # infrastructure/adapters/common/api_request_collector.py
    # Uses datetime.now(UTC) for request timestamp when caller doesn't provide one.
    # This is for audit/debugging metadata, not Bronze/Silver/Gold data determinism.
    "adapters/common/api_request_collector.py",
}


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
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    relative_path = _relative_infrastructure_path(py_file)
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
        violations = []

        for py_file in infrastructure_python_files:
            relative_path = _relative_infrastructure_path(py_file)
            if relative_path in ALLOWED_PATHS:
                continue
            violations.extend(_datetime_now_calls(py_file))

        assert not violations, (
            "datetime.now()/utcnow() found in infrastructure layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nTimestamps should be created in application layer "
            "(e.g., PipelineContext.started_at) and passed as parameters. "
            "See ADR-014."
        )

    def test_allowed_paths_still_exist_and_are_unambiguous(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Verify that path-based exceptions still exist and avoid basename drift.

        This prevents stale exceptions from accumulating and blocks future
        reintroduction of ambiguous basename-based exemptions like `client.py`.
        """
        existing_paths = {
            _relative_infrastructure_path(py_file)
            for py_file in infrastructure_python_files
        }
        missing = ALLOWED_PATHS - existing_paths

        assert not missing, (
            f"ALLOWED_PATHS contains non-existent files: {missing}. "
            "Remove stale entries from the allowed list."
        )

        basename_to_paths: dict[str, list[str]] = {}
        for path_str in existing_paths:
            basename_to_paths.setdefault(Path(path_str).name, []).append(path_str)

        ambiguous = {
            allowed_path: sorted(basename_to_paths[Path(allowed_path).name])
            for allowed_path in ALLOWED_PATHS
            if len(basename_to_paths.get(Path(allowed_path).name, [])) > 1
        }

        assert not ambiguous, (
            "ALLOWED_PATHS must stay basename-unique to prevent silent widening of "
            f"datetime exceptions: {ambiguous}"
        )

    def test_allowed_paths_still_require_exception(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Force removal of allowlist entries once datetime usage is refactored away."""
        file_by_path = {
            _relative_infrastructure_path(py_file): py_file
            for py_file in infrastructure_python_files
        }
        stale_exemptions = [
            allowed_path
            for allowed_path in sorted(ALLOWED_PATHS)
            if not _datetime_now_calls(file_by_path[allowed_path])
        ]

        assert not stale_exemptions, (
            "Remove stale datetime exceptions that no longer need allowlisting: "
            f"{stale_exemptions}"
        )
