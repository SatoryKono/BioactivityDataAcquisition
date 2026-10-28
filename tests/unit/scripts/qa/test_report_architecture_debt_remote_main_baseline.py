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
"""Unit tests for architecture debt remote-main baseline helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.engineering.qa import (
    report_architecture_debt_remote_main_baseline as baseline,
)

pytestmark = pytest.mark.unit


def _committed_git_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
    )
    tracked = repo / "tracked.txt"
    tracked.write_bytes(b"blob contents\n")
    directory_entry = repo / "directory-as-blob.json"
    directory_entry.mkdir()
    (directory_entry / "nested.txt").write_bytes(b"nested contents\n")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "directory-as-blob.json"], check=True
    )
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-C",
            str(repo),
            "commit",
            "-q",
            "-m",
            "test commit",
        ],
        check=True,
    )
    revision = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    return repo, revision


def test_git_blob_returns_existing_blob(tmp_path: Path) -> None:
    repo, revision = _committed_git_repo(tmp_path)

    assert baseline._git_blob(repo, revision, "tracked.txt") == b"blob contents\n"


def test_git_blob_returns_none_for_missing_path_in_valid_commit(tmp_path: Path) -> None:
    repo, revision = _committed_git_repo(tmp_path)

    assert baseline._git_blob(repo, revision, "missing.txt") is None


def test_git_blob_raises_for_directory_at_expected_path(tmp_path: Path) -> None:
    repo, revision = _committed_git_repo(tmp_path)

    with pytest.raises(RuntimeError, match="directory-as-blob.json.*tree, not a blob"):
        baseline._git_blob(repo, revision, "directory-as-blob.json")


def test_git_blob_raises_for_unresolvable_commit(tmp_path: Path) -> None:
    repo, _ = _committed_git_repo(tmp_path)

    with pytest.raises(RuntimeError, match="commit resolution"):
        baseline._git_blob(repo, "missing-revision", "tracked.txt")


def test_git_blob_raises_when_existing_blob_cannot_be_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, revision = _committed_git_repo(tmp_path)
    original_run = subprocess.run

    def fail_blob_read(
        args: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:2] == ["git", "show"]:
            return subprocess.CompletedProcess(
                args,
                128,
                stdout=b"",
                stderr=b"fatal: unable to read object",
            )
        return original_run(args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(baseline.subprocess, "run", fail_blob_read)

    with pytest.raises(RuntimeError, match="blob read.*unable to read object"):
        baseline._git_blob(repo, revision, "tracked.txt")


def test_json_blob_summary_returns_unavailable_for_none_blob() -> None:
    """_json_blob_summary should return availability:False when blob is None."""
    summary = baseline._json_blob_summary(None)

    assert summary == {"available": False}


def test_json_blob_summary_extracts_keys_from_valid_json_blob() -> None:
    """_json_blob_summary should extract expected keys from a valid JSON dict blob."""
    payload = {
        "schema_version": 1,
        "integral_score": 42,
        "weights_sum": 100,
        "coverage_xml_sha256": "abc123",
        "source_tree_sha256": "def456",
        "snapshot_date": "2026-09-01",
        "valid": True,
        "blocking_issue_count": 0,
        "extra_field": "ignored",
        "summary": {
            "source_module_count": 120,
            "unmeasured_module_count": 5,
            "repo_wide_untriaged_zero_import_candidate_count": 2,
            "retained_entrypoint_count": 10,
            "extra_nested": "ignored",
        },
    }
    blob = json.dumps(payload).encode("utf-8")

    summary = baseline._json_blob_summary(blob)

    assert summary["available"] is True
    assert summary["schema_version"] == 1
    assert summary["integral_score"] == 42
    assert summary["weights_sum"] == 100
    assert summary["coverage_xml_sha256"] == "abc123"
    assert summary["source_tree_sha256"] == "def456"
    assert summary["snapshot_date"] == "2026-09-01"
    assert summary["valid"] is True
    assert summary["blocking_issue_count"] == 0
    assert summary["source_module_count"] == 120
    assert summary["unmeasured_module_count"] == 5
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 2
    assert summary["retained_entrypoint_count"] == 10
    assert "extra_field" not in summary
    assert "extra_nested" not in summary


def test_json_blob_summary_rejects_git_conflict_markers() -> None:
    """_json_blob_summary should reject conflict-marker-contaminated blobs."""
    conflict_blob_text = """\
<<<<<<< HEAD
|||||||
=======
{
  "schema_version": 1,
  "integral_score": 99,
  "summary": {
    "source_module_count": 200
  }
}
>>>>>>> branch-name
"""
    blob = conflict_blob_text.encode("utf-8")

    summary = baseline._json_blob_summary(blob)

    assert summary == {"available": False, "conflict_markers_detected": True}


def test_json_blob_summary_returns_available_only_for_invalid_json() -> None:
    """_json_blob_summary should return only availability for invalid JSON."""
    blob = b"not valid JSON at all"

    summary = baseline._json_blob_summary(blob)

    assert summary == {"available": True}


def test_markdown_semantically_equivalent_masks_volatile_local_tracking_ref() -> None:
    """_markdown_semantically_equivalent should ignore changes to local_tracking_ref_matches_remote."""
    base_md = """# Title
- evidence_source: `tree`
- local_tracking_ref_matches_remote: `{status}`
| col |
| --- |
"""
    actual_md = base_md.format(status="True")
    expected_md = base_md.format(status="False")

    assert baseline._markdown_semantically_equivalent(actual_md, expected_md) is True

    # Real content drift should still be detected
    different_md = base_md.format(status="True") + "| row |\n"
    assert baseline._markdown_semantically_equivalent(actual_md, different_md) is False


def test_json_blob_summary_returns_available_only_for_non_dict_json() -> None:
    """_json_blob_summary should return only availability for blobs whose JSON content is not a dict."""
    blob = json.dumps(["valid", "json", "list"]).encode("utf-8")

    summary = baseline._json_blob_summary(blob)

    assert summary == {"available": True}


def _sample_baseline_markdown(
    *,
    status: str = "True",
    evidence_source: str = "remote_main_git_tree",
    fingerprint: str = "abc123",
    table_row: str = (
        "| `reports/quality/example.json` | `hash` | `True` | `True` | `False` |"
    ),
) -> str:
    return "\n".join(
        [
            "# Architecture Debt Remote-Main Baseline",
            "",
            f"- evidence_source: `{evidence_source}`",
            f"- baseline_artifact_fingerprint: `{fingerprint}`",
            f"- local_tracking_ref_matches_remote: `{status}`",
            "",
            "| artifact | blob_sha256 | available | required_on_remote | introduced_after_remote_main |",
            "| --- | --- | --- | --- | --- |",
            table_row,
            "",
        ]
    )


@pytest.mark.parametrize(
    ("actual_status", "expected_status"),
    [("True", "False"), ("False", "True")],
)
def test_markdown_equivalent_accepts_either_exact_tracking_boolean(
    actual_status: str,
    expected_status: str,
) -> None:
    """Only the exact tracking-status boolean may differ."""
    actual = _sample_baseline_markdown(status=actual_status)
    expected = _sample_baseline_markdown(status=expected_status)

    assert baseline._markdown_semantically_equivalent(actual, expected) is True


def test_markdown_equivalent_accepts_unchanged_document() -> None:
    """Identical Markdown remains equivalent without using the mask."""
    document = _sample_baseline_markdown(status="False")

    assert baseline._markdown_semantically_equivalent(document, document) is True


@pytest.mark.parametrize(
    "expected",
    [
        _sample_baseline_markdown(fingerprint="def456"),
        _sample_baseline_markdown(evidence_source="working_tree"),
        _sample_baseline_markdown(
            table_row=(
                "| `reports/quality/example.json` | `other` | `True` | `True` | `False` |"
            )
        ),
        _sample_baseline_markdown().replace(
            "- local_tracking_ref_matches_remote: `True`\n",
            "",
        ),
        _sample_baseline_markdown().replace(
            "- local_tracking_ref_matches_remote: `True`",
            "- local_tracking_ref_matches_remote: True",
        ),
        _sample_baseline_markdown().replace(
            "- local_tracking_ref_matches_remote: `True`",
            "- local_tracking_ref_matches_remote: `yes`",
        ),
        _sample_baseline_markdown().replace(
            "- local_tracking_ref_matches_remote: `True`",
            "  - local_tracking_ref_matches_remote: `False`",
        ),
        _sample_baseline_markdown(
            table_row=(
                "| `local_tracking_ref_matches_remote` | `False` | `True` | `True` | `False` |"
            )
        ),
    ],
)
def test_markdown_equivalent_rejects_non_tracking_or_malformed_drift(
    expected: str,
) -> None:
    """Fingerprint, evidence, tables, and inexact status lines stay significant."""
    actual = _sample_baseline_markdown(status="True")

    assert baseline._markdown_semantically_equivalent(actual, expected) is False


def _tracking_check_payload(*, matches_remote: bool) -> dict[str, object]:
    return {
        "evidence_source": "remote_main_git_tree",
        "remote_main_ref": "refs/heads/main",
        "baseline_artifact_fingerprint": "abc123",
        "local_tracking_ref_matches_remote": matches_remote,
        "artifacts": [
            {
                "path": "reports/quality/example.json",
                "blob_sha256": "hash",
                "required_on_remote": False,
                "summary": {"available": True},
            }
        ],
    }


def test_check_artifacts_rejects_live_tracking_ref_mismatch(tmp_path: Path) -> None:
    """Markdown masking must not accept a live local-ref mismatch."""
    payload = _tracking_check_payload(matches_remote=False)
    json_out = tmp_path / "baseline.json"
    md_out = tmp_path / "baseline.md"
    json_out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    masked_markdown = baseline.render_markdown(
        _tracking_check_payload(matches_remote=True)
    )
    expected_markdown = baseline.render_markdown(payload)
    assert baseline._markdown_semantically_equivalent(
        masked_markdown, expected_markdown
    )
    md_out.write_text(masked_markdown, encoding="utf-8")

    errors = baseline._check_artifacts(
        payload,
        json_out=json_out,
        md_out=md_out,
        root=tmp_path,
    )

    assert (
        "Local tracking ref does not match remote main; fetch before closeout" in errors
    )
    assert not any("Markdown artifact is stale" in error for error in errors)

    matching_payload = _tracking_check_payload(matches_remote=True)
    json_out.write_text(
        json.dumps(matching_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(baseline.render_markdown(matching_payload), encoding="utf-8")
    assert (
        baseline._check_artifacts(
            matching_payload,
            json_out=json_out,
            md_out=md_out,
            root=tmp_path,
        )
        == []
    )
