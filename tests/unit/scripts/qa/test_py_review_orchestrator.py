from __future__ import annotations

import pytest

from pathlib import Path

from scripts.engineering.qa.py_review_orchestrator import (
    ReviewOrchestrator,
    SectorResult,
)


pytestmark = pytest.mark.unit


def test_determine_subsectors_tracks_current_repo_layout(tmp_path: Path) -> None:
    for rel_path in (
        "configs/entities",
        "configs/composites",
        "configs/contracts",
        "configs/providers",
        "configs/base",
        "configs/quality",
        "configs/_schema",
        "configs/enums",
        "docs/00-project",
        "docs/01-requirements",
        "docs/02-architecture",
        "docs/03-guides",
        "docs/04-reference",
        "docs/05-operations",
        "docs/reports",
        "docs/plans",
    ):
        (tmp_path / rel_path).mkdir(parents=True, exist_ok=True)

    orchestrator = ReviewOrchestrator(
        repo_root=tmp_path, reports_dir=tmp_path / "reports" / "review"
    )

    config_subsectors = orchestrator.determine_subsectors("S7", ["configs"])
    doc_subsectors = orchestrator.determine_subsectors("S8", ["docs"])

    config_paths = {
        path for subsector in config_subsectors for path in subsector["paths"]
    }
    doc_paths = {path for subsector in doc_subsectors for path in subsector["paths"]}

    assert "configs/pipelines" not in config_paths
    assert "configs/infrastructure" not in config_paths
    assert "configs/composites" in config_paths
    assert "configs/providers" in config_paths
    assert "docs/03-data-model" not in doc_paths
    assert "docs/03-guides" in doc_paths
    assert "docs/reports" in doc_paths
    assert "docs/plans" in doc_paths


def test_runtime_boundary_import_is_reported_even_when_file_uses_type_checking(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "src" / "bioetl" / "application" / "sample.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from bioetl.infrastructure.adapters.fake import FakeAdapter\n"
        "import bioetl.infrastructure.adapters.real as real_adapter\n",
        encoding="utf-8",
    )

    orchestrator = ReviewOrchestrator(
        repo_root=tmp_path, reports_dir=tmp_path / "reports" / "review"
    )
    issues = orchestrator.analyze_python_file(file_path, "S2")

    arch_issues = [issue for issue in issues if issue.rule_id == "ARCH-001"]
    assert len(arch_issues) == 1
    assert arch_issues[0].line == 4


def test_allowed_constructor_is_not_reported_as_di_violation(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "bioetl" / "application" / "sample.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "from pathlib import Path\n\n"
        "class Sample:\n"
        "    def __init__(self) -> None:\n"
        "        self.output_path = Path('out.txt')\n",
        encoding="utf-8",
    )

    orchestrator = ReviewOrchestrator(
        repo_root=tmp_path, reports_dir=tmp_path / "reports" / "review"
    )
    issues = orchestrator.analyze_python_file(file_path, "S2")

    assert all(issue.rule_id != "AP-001" for issue in issues)


def test_final_report_uses_detected_rules_version(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "│   │   └── RULES.md          # Project governance (v9.9.9)\n",
        encoding="utf-8",
    )
    reports_dir = tmp_path / "reports" / "review"
    orchestrator = ReviewOrchestrator(repo_root=tmp_path, reports_dir=reports_dir)

    orchestrator.write_final_report(
        [
            SectorResult(
                sector_id="S1",
                sector_name="Domain",
                scope_paths=["src/bioetl/domain"],
                files_reviewed=1,
                total_loc=10,
            )
        ]
    )

    report = (reports_dir / "FINAL-REVIEW.md").read_text(encoding="utf-8")
    assert "**RULES.md Version**: 9.9.9" in report
