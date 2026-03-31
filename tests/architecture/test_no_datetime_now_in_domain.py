"""Architecture test: current time creation is restricted in the domain layer.

REQ-ARCH-031: Single source of truth for timestamps.
Domain business paths must receive timestamps explicitly instead of creating
them implicitly at read/transition time.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

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
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    relative_path = _relative_domain_path(py_file)
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


class TestNoDatetimeNowInDomain:
    """Tests ensuring domain business paths don't create implicit timestamps."""

    @pytest.fixture
    def domain_python_files(self) -> list[Path]:
        """Get all Python files in domain directory."""
        base = _domain_base()
        return list(base.rglob("*.py"))

    def test_no_datetime_now_in_domain(
        self, domain_python_files: list[Path]
    ) -> None:
        """Domain MUST NOT call datetime.now() outside sanctioned seams."""
        violations: list[str] = []

        for py_file in domain_python_files:
            relative_path = _relative_domain_path(py_file)
            if relative_path in ALLOWED_PATHS:
                continue
            violations.extend(_datetime_now_calls(py_file))

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
        existing_paths = {
            _relative_domain_path(py_file)
            for py_file in domain_python_files
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
            f"domain datetime exceptions: {ambiguous}"
        )

    def test_allowed_paths_still_require_exception(
        self, domain_python_files: list[Path]
    ) -> None:
        """Force removal of allowlist entries once datetime usage is refactored away."""
        file_by_path = {
            _relative_domain_path(py_file): py_file
            for py_file in domain_python_files
        }
        stale_exemptions = [
            allowed_path
            for allowed_path in sorted(ALLOWED_PATHS)
            if not _datetime_now_calls(file_by_path[allowed_path])
        ]

        assert not stale_exemptions, (
            "Remove stale domain datetime exceptions that no longer need allowlisting: "
            f"{stale_exemptions}"
        )
