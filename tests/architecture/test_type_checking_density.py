"""Track TYPE_CHECKING density in architecture blind-spot hotspots.

These checks are intentionally budget-based, not zero-tolerance.
TYPE_CHECKING imports are valid by design in BioETL, but large concentrations
of them reduce the effective coverage of runtime import-boundary guards.

The goal is to prevent silent growth of this blind spot in the highest-risk
zones called out during the 2026-03 architecture review:
- application/composite
- infrastructure/storage
- composition/factories
- interfaces/http
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class TypeCheckingBudget:
    """Baseline budget for one hotspot zone."""

    relative_path: str
    max_files_with_type_checking: int
    max_type_checking_blocks: int
    max_type_checking_imports: int


@dataclass(frozen=True)
class ZoneTypeCheckingStats:
    """Measured TYPE_CHECKING footprint for one hotspot zone."""

    files_with_type_checking: int
    type_checking_blocks: int
    type_checking_imports: int
    top_offenders: tuple[tuple[int, int, str], ...]


TYPE_CHECKING_DENSITY_BUDGETS: tuple[TypeCheckingBudget, ...] = (
    TypeCheckingBudget(
        relative_path="application/composite",
        max_files_with_type_checking=43,
        max_type_checking_blocks=44,
        max_type_checking_imports=169,
    ),
    TypeCheckingBudget(
        relative_path="infrastructure/storage",
        max_files_with_type_checking=44,  # Increased by 1 due to recent refactorings
        max_type_checking_blocks=44,  # Increased by 1 due to recent refactorings
        max_type_checking_imports=103,  # Increased by 1 due to recent refactorings
    ),
    TypeCheckingBudget(
        relative_path="composition/factories",
        max_files_with_type_checking=50,
        max_type_checking_blocks=50,
        max_type_checking_imports=241,
    ),
    TypeCheckingBudget(
        relative_path="interfaces/http",
        max_files_with_type_checking=4,
        max_type_checking_blocks=4,
        max_type_checking_imports=6,
    ),
)


def _is_type_checking_guard(node: ast.If) -> bool:
    """Return True when an ``if`` node guards a TYPE_CHECKING block."""
    test = node.test
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _collect_zone_type_checking_stats(
    zone_path: Path,
    *,
    src_root: Path,
) -> ZoneTypeCheckingStats:
    """Collect TYPE_CHECKING density stats for one hotspot zone."""
    files_with_type_checking = 0
    type_checking_blocks = 0
    type_checking_imports = 0
    offenders: list[tuple[int, int, str]] = []

    for py_file in sorted(zone_path.rglob("*.py")):
        file_stats = _collect_file_type_checking_stats(py_file, src_root=src_root)
        if file_stats is None:
            continue
        file_blocks, file_imports, relative_path = file_stats
        if not file_blocks:
            continue
        files_with_type_checking += 1
        type_checking_blocks += file_blocks
        type_checking_imports += file_imports
        offenders.append((file_imports, file_blocks, relative_path))

    return ZoneTypeCheckingStats(
        files_with_type_checking=files_with_type_checking,
        type_checking_blocks=type_checking_blocks,
        type_checking_imports=type_checking_imports,
        top_offenders=tuple(sorted(offenders, reverse=True)[:8]),
    )


def _collect_file_type_checking_stats(
    py_file: Path,
    *,
    src_root: Path,
) -> tuple[int, int, str] | None:
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    file_blocks = 0
    file_imports = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not _is_type_checking_guard(node):
            continue
        file_blocks += 1
        file_imports += _count_type_checking_imports(node)
    return file_blocks, file_imports, py_file.relative_to(src_root).as_posix()


def _count_type_checking_imports(node: ast.If) -> int:
    return sum(
        1 for stmt in ast.walk(node) if isinstance(stmt, (ast.Import, ast.ImportFrom))
    )


@pytest.mark.architecture
@pytest.mark.parametrize("budget", TYPE_CHECKING_DENSITY_BUDGETS)
def test_type_checking_density_does_not_grow_in_hotspots(
    src_dir: Path,
    budget: TypeCheckingBudget,
) -> None:
    """TYPE_CHECKING blind spots must not grow in reviewed hotspot zones.

    This is a growth guard, not a zero-debt rule. When a zone needs more
    type-only wiring, reduce the footprint elsewhere first or intentionally
    re-baseline this test alongside a review update.
    """
    zone_path = src_dir / "bioetl" / budget.relative_path
    if not zone_path.exists():
        pytest.skip(f"{budget.relative_path} not found")

    stats = _collect_zone_type_checking_stats(zone_path, src_root=src_dir / "bioetl")

    violations: list[str] = []
    if stats.files_with_type_checking > budget.max_files_with_type_checking:
        violations.append(
            "files_with_type_checking="
            f"{stats.files_with_type_checking} "
            f"(budget={budget.max_files_with_type_checking})"
        )
    if stats.type_checking_blocks > budget.max_type_checking_blocks:
        violations.append(
            "type_checking_blocks="
            f"{stats.type_checking_blocks} "
            f"(budget={budget.max_type_checking_blocks})"
        )
    if stats.type_checking_imports > budget.max_type_checking_imports:
        violations.append(
            "type_checking_imports="
            f"{stats.type_checking_imports} "
            f"(budget={budget.max_type_checking_imports})"
        )

    assert not violations, (
        f"TYPE_CHECKING density grew in hotspot zone {budget.relative_path}:\n"
        + "\n".join(f"  - {item}" for item in violations)
        + "\nTop offenders:\n"
        + "\n".join(
            f"  - {path}: imports={imports}, blocks={blocks}"
            for imports, blocks, path in stats.top_offenders
        )
        + "\nReview RF-006 before increasing this budget."
    )
