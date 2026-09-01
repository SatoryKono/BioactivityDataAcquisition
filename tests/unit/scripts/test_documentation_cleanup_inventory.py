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
"""Unit coverage for documentation cleanup inventory link handling."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_safe_iter_local_doc_tree_reports_quarantined_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Local docs/report scans should skip quarantined paths without crashing."""
    reports_root = tmp_path / "docs" / "reports"
    reports_root.mkdir(parents=True)
    (reports_root / "index.md").write_text("# Reports\n", encoding="utf-8")
    quarantined = reports_root / ".quarantined-corrupt-evidence"
    quarantined.mkdir()
    (quarantined / "broken.md").write_text("# Do not scan\n", encoding="utf-8")
    monkeypatch.setattr(inventory, "PROJECT_ROOT", tmp_path)

    paths, errors = inventory._safe_iter_local_doc_tree("docs/reports")

    assert paths == ["docs/reports/index.md"]
    assert errors == [
        {
            "path": "docs/reports/.quarantined-corrupt-evidence",
            "error": "QuarantinedPath",
        }
    ]


def test_safe_iter_local_doc_tree_ignores_transient_link_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CI link report must not make the cleanup inventory self-invalidating."""
    reports_root = tmp_path / "docs" / "reports"
    reports_root.mkdir(parents=True)
    (reports_root / "index.md").write_text("# Reports\n", encoding="utf-8")
    (reports_root / "docs-link-check-report.json").write_text(
        '{"status": "ok"}\n', encoding="utf-8"
    )
    monkeypatch.setattr(inventory, "PROJECT_ROOT", tmp_path)

    paths, errors = inventory._safe_iter_local_doc_tree("docs/reports")

    assert paths == ["docs/reports/index.md"]
    assert errors == []


def test_inventory_field_diffs_reports_link_count_and_row_changes() -> None:
    """--check should name the stale file fields instead of only the JSON path."""
    generated = {
        "summary": {"total_doc_like": 2},
        "files": [
            {
                "path": "docs/05-operations/runbooks/index.md",
                "outbound_links": 47,
            },
            {
                "path": "docs/05-operations/runbooks/docker-security-baseline.md",
                "inbound_links": 1,
            },
        ],
    }
    committed = {
        "summary": {"total_doc_like": 1},
        "files": [
            {
                "path": "docs/05-operations/runbooks/index.md",
                "outbound_links": 46,
            },
        ],
    }

    diffs = inventory._inventory_field_diffs(generated, committed, limit=12)

    assert (
        "  files[docs/05-operations/runbooks/docker-security-baseline.md]: "
        "generated-only"
    ) in diffs
    assert (
        "  files[docs/05-operations/runbooks/index.md].outbound_links: "
        "generated=47 committed=46"
    ) in diffs
    assert "  summary.total_doc_like: generated=2 committed=1" in diffs


def test_inventory_field_diffs_respects_limit() -> None:
    generated = {
        "files": [
            {"path": f"docs/generated-only-{index:02d}.md"} for index in range(20)
        ]
    }
    committed: dict[str, object] = {"files": []}

    diffs = inventory._inventory_field_diffs(generated, committed, limit=12)

    assert len(diffs) == 12
    assert diffs[0] == "  files[docs/generated-only-00.md]: generated-only"
    assert diffs[-1] == "  files[docs/generated-only-11.md]: generated-only"


def test_inventory_field_diffs_summary_only() -> None:
    files = [{"path": "docs/05-operations/runbooks/index.md", "outbound_links": 47}]
    generated = {"summary": {"total_doc_like": 2}, "files": files}
    committed = {"summary": {"total_doc_like": 1}, "files": files}

    diffs = inventory._inventory_field_diffs(generated, committed, limit=12)

    assert diffs == ["  summary.total_doc_like: generated=2 committed=1"]


def test_main_check_mode_returns_one_on_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(inventory, "PROJECT_ROOT", tmp_path)
    json_output = tmp_path / "documentation-cleanup-inventory.json"
    markdown_output = tmp_path / "documentation-cleanup-inventory.md"
    json_output.write_text("{}\n", encoding="utf-8", newline="\n")
    markdown_output.write_text("# stale\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(
        inventory,
        "_build_inventory",
        lambda: {"summary": {"total_doc_like": 1}, "files": []},
    )
    monkeypatch.setattr(inventory, "_render_markdown", lambda _payload: "# current\n")

    exit_code = inventory.main(
        [
            "--check",
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[drift] mismatch:" in captured.out


def test_check_inventory_drift_includes_json_field_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JSON mismatches must surface compact field diffs for docs-cycle edits."""
    monkeypatch.setattr(inventory, "PROJECT_ROOT", tmp_path)
    json_output = tmp_path / "documentation-cleanup-inventory.json"
    markdown_output = tmp_path / "documentation-cleanup-inventory.md"
    generated_payload = {
        "files": [
            {
                "path": "docs/05-operations/runbooks/index.md",
                "outbound_links": 47,
            }
        ]
    }
    json_output.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "docs/05-operations/runbooks/index.md",
                        "outbound_links": 46,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    markdown_output.write_text("# stale\n", encoding="utf-8", newline="\n")
    json_content = (
        json.dumps(generated_payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )

    mismatches, details = inventory._check_inventory_drift(
        json_output=json_output,
        markdown_output=markdown_output,
        json_content=json_content,
        md_content="# current\n",
    )

    assert mismatches == [
        "documentation-cleanup-inventory.json",
        "documentation-cleanup-inventory.md",
    ]
    assert any("outbound_links" in line for line in details)


def test_generated_route_violations_reports_unowned_generated_rows() -> None:
    """Generator checks must fail when generated docs lack route ownership."""
    payload = {
        "files": [
            {
                "path": "docs/generated/unowned.md",
                "status": "Generated",
                "generated_route": None,
                "generated_route_exception": None,
            },
            {
                "path": "docs/generated/owned.md",
                "status": "Generated",
                "generated_route": "owned-route",
                "generated_route_exception": None,
            },
            {
                "path": "docs/generated/exception.md",
                "status": "Generated",
                "generated_route": None,
                "generated_route_exception": "diagram_kind:diagram_support",
            },
        ]
    }

    assert inventory._generated_route_violations(payload) == [
        "docs/generated/unowned.md"
    ]


def test_historical_docs_report_is_retained_without_repeated_migration() -> None:
    """An explicit historical marker resolves a report's cleanup disposition."""
    assert inventory._classify(
        "docs/reports/documentation-audit-report-2026-07-13.md",
        "Status: historical\nClass: internal-published\n",
        duplicate_group=None,
        route=None,
        lifecycle="docs_reports_curated_or_historical_report",
    ) == ("Archived", "historical", "keep")
