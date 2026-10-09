"""Tests for batch issue closeout evaluation without producer reruns."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from memory.proof import VerificationResult
from scripts.engineering.qa import issue_closeout_batch

pytestmark = pytest.mark.unit


def _bundle() -> dict[str, object]:
    return {
        "run_id": "proof-42",
        "bundle_digest": "a" * 64,
        "source": {"head_sha": "b" * 40},
        "repository": {"ci_run_id": "circle-42"},
        "receipts": [
            {
                "receipt_id": "architecture",
                "evidence_kind": "tests",
                "status": "pass",
                "output_digest": "c" * 64,
            },
            {
                "receipt_id": "governance",
                "evidence_kind": "governance",
                "status": "pass",
                "output_digest": "d" * 64,
            },
        ],
    }


def _manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "batch_id": "wave-1",
        "issues": [
            {
                "number": 101,
                "criteria": [
                    {
                        "id": "complete-proof",
                        "description": "Полный bundle принят",
                        "requires": {"bundle_outcome": "ADMIT"},
                    },
                    {
                        "id": "architecture",
                        "description": "Архитектурные проверки прошли",
                        "requires": {"receipt_id": "architecture"},
                    },
                ],
            },
            {
                "number": 102,
                "criteria": [
                    {
                        "id": "governance",
                        "description": "Governance checks прошли",
                        "requires": {"evidence_kind": "governance"},
                    }
                ],
            },
        ],
    }


def _admit(*args: object, **kwargs: object) -> VerificationResult:
    return VerificationResult("ADMIT", True, (), ())


def test_one_verified_bundle_marks_multiple_issues_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(issue_closeout_batch, "verify_bundle", _admit)

    report, exit_code = issue_closeout_batch.evaluate_batch(
        bundle=_bundle(), manifest=_manifest(), repo_root=Path.cwd()
    )

    assert exit_code == 0
    assert report["status"] == "ready"
    assert report["execution"] == {
        "evidence_producer_runs": 0,
        "issues_evaluated": 2,
        "ready_count": 2,
        "not_ready_count": 0,
    }
    assert [issue["number"] for issue in report["issues"]] == [101, 102]


def test_missing_receipt_keeps_only_affected_issue_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(issue_closeout_batch, "verify_bundle", _admit)
    manifest = _manifest()
    manifest["issues"][1]["criteria"][0]["requires"] = {"receipt_id": "missing"}

    report, exit_code = issue_closeout_batch.evaluate_batch(
        bundle=_bundle(), manifest=manifest, repo_root=Path.cwd()
    )

    assert exit_code == 2
    assert report["status"] == "not_ready"
    assert [issue["status"] for issue in report["issues"]] == [
        "ready",
        "not_ready",
    ]


def test_stopped_bundle_cannot_mark_any_issue_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        issue_closeout_batch,
        "verify_bundle",
        lambda **kwargs: VerificationResult("STOP", False, ("stale",), ()),
    )

    report, exit_code = issue_closeout_batch.evaluate_batch(
        bundle=_bundle(), manifest=_manifest(), repo_root=Path.cwd()
    )

    assert exit_code == 2
    assert report["execution"]["ready_count"] == 0
    assert all(issue["status"] == "not_ready" for issue in report["issues"])


def test_manifest_rejects_duplicate_issue_numbers() -> None:
    manifest = _manifest()
    manifest["issues"].append(manifest["issues"][0])
    schema = json.loads(
        issue_closeout_batch.DEFAULT_MANIFEST_SCHEMA.read_text(encoding="utf-8")
    )

    with pytest.raises(ValueError, match="duplicate issue number: 101"):
        issue_closeout_batch._validate_manifest(manifest, schema)


def test_output_must_stay_below_reports(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="below REPO_ROOT/reports"):
        issue_closeout_batch._safe_output(tmp_path / "outside.json", tmp_path)


def test_repo_root_cannot_be_rebased_by_cli(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="refusing path outside"):
        issue_closeout_batch._trusted_repo_root(tmp_path)


def test_input_must_stay_below_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "bundle.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="refusing path outside"):
        issue_closeout_batch._safe_input(
            outside,
            label="bundle",
            repo_root=repo_root,
        )


def test_output_rejects_parent_escape_from_reports(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "reports").mkdir(parents=True)

    with pytest.raises(ValueError, match="below REPO_ROOT/reports"):
        issue_closeout_batch._safe_output(
            repo_root / "reports" / ".." / "escaped.json",
            repo_root,
        )


@pytest.mark.parametrize(
    "relative",
    ["NUL.json", "CONOUT$.json", "COM¹.json", "report:stream.json"],
)
def test_output_rejects_windows_special_names(tmp_path: Path, relative: str) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "reports").mkdir(parents=True)

    with pytest.raises(
        ValueError,
        match="unsafe path component|below REPO_ROOT/reports",
    ):
        issue_closeout_batch._safe_output(
            repo_root / "reports" / relative,
            repo_root,
        )


@pytest.mark.skipif(
    os.name != "nt", reason="NTFS alternate data streams are Windows-only"
)
def test_input_rejects_ntfs_alternate_data_stream(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    carrier = repo_root / "bundle.json"
    carrier.write_text("{}", encoding="utf-8")
    alternate_stream = Path(f"{carrier}:payload")
    alternate_stream.write_text(json.dumps(_bundle()), encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe path component"):
        issue_closeout_batch._safe_input(
            alternate_stream,
            label="bundle",
            repo_root=repo_root,
        )


def test_output_rejects_symlink_escape(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    reports = repo_root / "reports"
    outside = tmp_path / "outside"
    reports.mkdir(parents=True)
    outside.mkdir()
    link = reports / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Host does not permit symlink creation: {exc}")

    with pytest.raises(ValueError, match="below REPO_ROOT/reports"):
        issue_closeout_batch._safe_output(link / "escaped.json", repo_root)


def test_cli_rejects_untrusted_repo_root_without_writing(tmp_path: Path) -> None:
    untrusted_root = tmp_path / "untrusted"
    output = untrusted_root / "reports/escaped.json"

    exit_code = issue_closeout_batch.main(
        [
            "--bundle",
            "bundle.json",
            "--manifest",
            "manifest.yaml",
            "--output",
            str(output),
            "--repo-root",
            str(untrusted_root),
        ]
    )

    assert exit_code == 2
    assert not output.exists()


def test_cli_writes_report_without_running_producers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(issue_closeout_batch, "verify_bundle", _admit)
    repo_root = tmp_path / "repo"
    reports = repo_root / "reports"
    reports.mkdir(parents=True)
    inputs = repo_root / "inputs"
    inputs.mkdir()
    bundle_path = inputs / "bundle.json"
    manifest_path = inputs / "manifest.yaml"
    schema_path = repo_root / "configs/quality/issue_closeout_batch.schema.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(
        issue_closeout_batch.DEFAULT_MANIFEST_SCHEMA.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    output = reports / "quality/issue-closeout/wave-1.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    manifest_path.write_text(
        """schema_version: 1
batch_id: wave-1
issues:
  - number: 101
    criteria:
      - id: complete-proof
        description: Full proof admitted
        requires:
          bundle_outcome: ADMIT
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(issue_closeout_batch, "ROOT", repo_root)
    monkeypatch.chdir(tmp_path)

    exit_code = issue_closeout_batch.main(
        [
            "--bundle",
            str(bundle_path.relative_to(repo_root)),
            "--manifest",
            str(manifest_path.relative_to(repo_root)),
            "--output",
            str(output.relative_to(repo_root)),
            "--repo-root",
            str(repo_root),
            "--manifest-schema",
            str(schema_path.relative_to(repo_root)),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "ready"
    assert payload["execution"]["evidence_producer_runs"] == 0
