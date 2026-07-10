"""Unit coverage for documentation cleanup inventory link handling."""

from __future__ import annotations

import pytest

from scripts.docs.checks import documentation_cleanup_inventory as inventory

pytestmark = pytest.mark.unit


def test_outgoing_links_keeps_windows_absolute_paths() -> None:
    """Windows drive paths should be treated as local links, not URI schemes."""
    text = r"[evidence](E:\repo\reports\semantic_pipeline_audit\audit.md:12)"

    assert inventory._outgoing_links(text) == [
        r"E:\repo\reports\semantic_pipeline_audit\audit.md:12"
    ]


def test_resolve_link_maps_wsl_absolute_repo_alias_on_windows(
    monkeypatch,
) -> None:
    """WSL-style absolute links should resolve when PROJECT_ROOT is Windows-style."""
    class FakeRoot:
        def resolve(self) -> FakeRoot:
            return self

        def as_posix(self) -> str:
            return "E:/g-drive/05_AI/github/BioactivityDataAcquisition2"

    monkeypatch.setattr(inventory, "PROJECT_ROOT", FakeRoot())

    resolved = inventory._resolve_link(
        "reports/semantic_pipeline_audit/source.md",
        (
            "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/"
            "reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv:25"
        ),
    )

    assert (
        resolved
        == "reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv"
    )


def test_resolve_link_normalizes_relative_paths_without_filesystem() -> None:
    """Relative markdown targets should resolve lexically for deterministic inventory."""
    resolved = inventory._resolve_link(
        "docs/03-guides/source.md",
        "../02-architecture/decisions/ADR-001-example.md:12",
    )

    assert resolved == "docs/02-architecture/decisions/ADR-001-example.md"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".github/ISSUES/README.md", None),
        (
            ".github/ISSUES/ADR-HYGIENE-4746-Archive-ADR-003-ADR-008.md",
            4746,
        ),
        (".github/ISSUES/DOC-AUDIT-2026-06-19-ISSUE-PACK.md", None),
    ],
)
def test_github_issue_number_ignores_dates(path: str, expected: int | None) -> None:
    """Issue number extraction must not treat dates as live GitHub issue ids."""
    assert inventory._github_issue_number(path) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".github/ISSUES/CREATION_GUIDE.md", "guide"),
        (".github/ISSUES/CHEMBL-ISSUES-INDEX.md", "index"),
        (".github/ISSUES/DOC-AUDIT-2026-06-19-ISSUE-PACK.md", "issue_pack"),
        (
            ".github/ISSUES/ADR-HYGIENE-4746-Archive-ADR-003-ADR-008.md",
            "live_issue_mirror",
        ),
        (".github/ISSUES/PLAN-EXAMPLE.md", "active_draft"),
    ],
)
def test_github_issue_lifecycle(path: str, expected: str) -> None:
    """GitHub issue drafts need deterministic lifecycle buckets."""
    assert inventory._github_issue_lifecycle(path) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("docs/reports/index.md", "docs_reports_curated_entrypoint"),
        (
            "docs/reports/generated/documentation-cleanup-inventory.json",
            "docs_reports_generated_or_route_owned",
        ),
        (
            "docs/reports/evidence/project-test-health/SUMMARY.md",
            "docs_reports_retention_sensitive_evidence",
        ),
        (
            "reports/quality/tech-debt-issues-5847-5852-closeout.json",
            "closeout_evidence",
        ),
        ("reports/quality/dead-code-inventory.md", "active_quality_baseline"),
    ],
)
def test_reports_lifecycle(path: str, expected: str) -> None:
    """Reports surfaces must be distinguishable by cleanup lifecycle."""
    assert inventory._reports_lifecycle(path) == expected


def test_generated_route_exception_requires_generated_status() -> None:
    """Route exceptions are limited to generated rows with deterministic ownership."""
    assert (
        inventory._generated_route_exception(
            status="Generated",
            route=None,
            diagram_kind="diagram_support",
            lifecycle=None,
        )
        == "diagram_kind:diagram_support"
    )
    assert (
        inventory._generated_route_exception(
            status="Active",
            route=None,
            diagram_kind="diagram_support",
            lifecycle=None,
        )
        is None
    )
