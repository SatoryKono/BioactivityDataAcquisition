"""Shared helpers for repository-wide Python review orchestration."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final


@dataclass(frozen=True, slots=True)
class ReviewIssue:
    """One review finding tied to a source location."""

    rule_id: str
    message: str
    path: str
    line: int
    sector_id: str


@dataclass(slots=True)
class SectorResult:
    """Summary produced for one review sector."""

    sector_id: str
    sector_name: str
    scope_paths: list[str]
    files_reviewed: int
    total_loc: int
    issues: list[ReviewIssue] = field(default_factory=list)


_SUBSECTOR_CANDIDATES: Final[dict[str, tuple[str, ...]]] = {
    "S7": (
        "configs/entities",
        "configs/composites",
        "configs/contracts",
        "configs/providers",
        "configs/base",
        "configs/quality",
        "configs/_schema",
        "configs/enums",
    ),
    "S8": (
        "docs/00-project",
        "docs/01-requirements",
        "docs/02-architecture",
        "docs/03-guides",
        "docs/04-reference",
        "docs/05-operations",
        "docs/reports",
        "docs/plans",
    ),
}


class ReviewOrchestrator:
    """Coordinate deterministic local review helpers and report generation."""

    def __init__(self, *, repo_root: Path, reports_dir: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.reports_dir = reports_dir.resolve()

    def determine_subsectors(
        self, sector_id: str, scope_paths: list[str]
    ) -> list[dict[str, object]]:
        """Return existing, current-layout subsectors for a review sector."""
        candidates = _SUBSECTOR_CANDIDATES.get(
            sector_id, tuple(scope_paths)
        )
        result: list[dict[str, object]] = []
        for relative_path in candidates:
            if not (self.repo_root / relative_path).exists():
                continue
            result.append(
                {
                    "id": f"{sector_id}-{len(result) + 1}",
                    "name": Path(relative_path).name,
                    "paths": [relative_path],
                }
            )
        return result

    def analyze_python_file(
        self, file_path: Path, sector_id: str
    ) -> list[ReviewIssue]:
        """Report runtime application-to-infrastructure import violations."""
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        issues: list[ReviewIssue] = []
        relative_path = self._relative_path(file_path)

        for node in self._runtime_nodes(tree.body):
            imported_modules: tuple[str, ...]
            if isinstance(node, ast.Import):
                imported_modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules = (node.module or "",)
            else:
                continue

            if (
                "/application/" in f"/{relative_path}"
                and any(
                    module == "bioetl.infrastructure"
                    or module.startswith("bioetl.infrastructure.")
                    for module in imported_modules
                )
            ):
                issues.append(
                    ReviewIssue(
                        rule_id="ARCH-001",
                        message=(
                            "Application code imports infrastructure at runtime."
                        ),
                        path=relative_path,
                        line=node.lineno,
                        sector_id=sector_id,
                    )
                )
        return issues

    def write_final_report(self, results: list[SectorResult]) -> Path:
        """Write a compact deterministic final review report."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.reports_dir / "FINAL-REVIEW.md"
        rules_version = self._detect_rules_version()
        lines = [
            "# Final Python Review",
            "",
            f"**RULES.md Version**: {rules_version}",
            "",
            "## Sector Summary",
            "",
            "| Sector | Name | Files | LOC | Issues |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for result in results:
            lines.append(
                f"| {result.sector_id} | {result.sector_name} | "
                f"{result.files_reviewed} | {result.total_loc} | "
                f"{len(result.issues)} |"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return report_path

    def _relative_path(self, file_path: Path) -> str:
        try:
            return file_path.resolve().relative_to(self.repo_root).as_posix()
        except ValueError:
            return file_path.as_posix()

    @staticmethod
    def _runtime_nodes(nodes: list[ast.stmt]) -> list[ast.stmt]:
        runtime_nodes: list[ast.stmt] = []
        for node in nodes:
            if (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Name)
                and node.test.id == "TYPE_CHECKING"
            ):
                runtime_nodes.extend(ReviewOrchestrator._runtime_nodes(node.orelse))
                continue
            runtime_nodes.append(node)
            nested_bodies: list[list[ast.stmt]] = []
            if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                nested_bodies.append(node.body)
            for body in nested_bodies:
                runtime_nodes.extend(ReviewOrchestrator._runtime_nodes(body))
        return runtime_nodes

    def _detect_rules_version(self) -> str:
        rules_path = self.repo_root / "docs" / "00-project" / "RULES.md"
        if rules_path.is_file():
            match = re.search(
                r"(?im)^\s*Version:\s*['\"]?v?([0-9]+(?:\.[0-9]+)+)",
                rules_path.read_text(encoding="utf-8"),
            )
            if match:
                return match.group(1)

        readme_path = self.repo_root / "README.md"
        if readme_path.is_file():
            match = re.search(
                r"RULES\.md[^\n]*?\bv([0-9]+(?:\.[0-9]+)+)",
                readme_path.read_text(encoding="utf-8"),
            )
            if match:
                return match.group(1)
        return "unknown"
