"""Regression fixtures for the N1 nightly shadow archive."""

from __future__ import annotations

import inspect
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import scripts.engineering.ci.nightly_shadow_archive as archive_module
from scripts.engineering.ci.nightly_shadow_archive import (
    JOB_KINDS,
    ArchiveError,
    _atomic_create,
    aggregate_results,
    archive_runs,
    assess_shadow_window,
    canonical_bytes,
    job_duty,
    main,
    oracle_equivalent,
    oracle_pagination,
    REPO_ROOT,
    oracle_sha256,
    partition_bucket,
    partition_producer,
    require_accepted,
    verify_archive,
    write_snapshot,
)

pytestmark = pytest.mark.unit


def _results(**overrides: str) -> dict[str, str]:
    results = {
        name: "skipped"
        if kind in {"weekly_monday", "weekly_sunday", "quarterly"}
        else "success"
        for name, kind in JOB_KINDS.items()
    }
    results.update(overrides)
    return results


def _aggregate(results: dict[str, str], **kwargs: str) -> dict[str, object]:
    payload = {"dow": "Fri", "dom": "23", "month": "10", "force_weekly": "false"}
    payload.update(kwargs)
    return aggregate_results(results, **payload)


def _raw(run_id: int = 11, attempt: int = 1, head: str = "abc123") -> dict[str, object]:
    return {
        "conclusion": "success",
        "created_at": "2026-10-09T03:00:00Z",
        "event": "schedule",
        "head_sha": head,
        "id": run_id,
        "path": ".github/workflows/nightly.yml",
        "run_attempt": attempt,
    }


def _outcomes(
    *,
    fetched: int = 1,
    total: int | None = 1,
    hit_page_cap: bool = False,
) -> dict[str, object]:
    return {
        "jobs": [{"conclusion": "success", "name": "clock", "status": "completed"}],
        "pagination": {
            "hit_page_cap": hit_page_cap,
            "jobs_fetched": fetched,
            "jobs_total_count": total,
            "pages_fetched": 1,
            "status": oracle_pagination(fetched, total, hit_page_cap=hit_page_cap),
        },
        "schema_version": 1,
    }


def _manifest(raw: dict[str, object], outcomes: dict[str, object]) -> dict[str, object]:
    pagination = outcomes["pagination"]
    assert isinstance(pagination, dict)
    return {
        "action_sha": None,
        "action_sha_status": "missing",
        "base_sha": None,
        "conclusion": raw["conclusion"],
        "event": raw["event"],
        "head_sha": raw["head_sha"],
        "outcomes_sha256": oracle_sha256(canonical_bytes(outcomes)),
        "pagination_status": pagination["status"],
        "raw_sha256": oracle_sha256(canonical_bytes(raw)),
        "run_attempt": raw["run_attempt"],
        "run_id": raw["id"],
        "schema_version": 1,
        "tested_sha": raw["head_sha"],
        "timestamps": {"created_at": raw["created_at"]},
        "workflow_code_sha": raw["head_sha"],
        "workflow_code_sha_source": "head_sha",
        "workflow_path": raw["path"],
    }


def _store(root: Path, raw: dict[str, object], outcomes: dict[str, object]) -> Path:
    return write_snapshot(
        root,
        raw=raw,
        outcomes=outcomes,
        manifest=_manifest(raw, outcomes),
    )


def _seal_index(root: Path) -> None:
    rows = []
    for manifest_path in sorted(root.glob("run-*/attempt-*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        timestamps = manifest["timestamps"]
        rows.append(
            {
                "conclusion": manifest["conclusion"],
                "created_at": timestamps["created_at"],
                "event": manifest["event"],
                "head_sha": manifest["head_sha"],
                "pagination_status": manifest["pagination_status"],
                "raw_sha256": manifest["raw_sha256"],
                "run_attempt": manifest["run_attempt"],
                "run_id": manifest["run_id"],
            }
        )
    (root / "index.json").write_bytes(canonical_bytes(rows))


def test_oracle_does_not_use_the_schedule_classifier() -> None:
    """The oracle compares stored values and does not decide weekly duty."""

    for function in (oracle_equivalent, oracle_pagination, oracle_sha256):
        source = inspect.getsource(function)
        assert "job_duty" not in source
        assert "force_weekly" not in source
    compared = oracle_equivalent(
        {"codeql": "skipped"},
        {"codeql": "success"},
        job_names=["codeql"],
    )
    assert compared["equivalent"] is False
    assert compared["mismatches"][0]["left"] == "skipped"


@pytest.mark.parametrize("missing", [None, "", "missing"])
def test_equivalence_rejects_missing_observations(missing: object) -> None:
    for left, right in (
        ({}, {}),
        ({"tests": missing}, {"tests": missing}),
        ({"tests": "success"}, {}),
    ):
        compared = oracle_equivalent(left, right, job_names=["tests"])
        assert compared["equivalent"] is False
        assert compared["mismatches"][0]["job"] == "tests"


@pytest.mark.parametrize(
    ("daily", "validators", "expected"),
    [
        ("success", "success", "success"),
        ("failure", "success", "non_success"),
        ("success", "failure", "non_success"),
        ("cancelled", "skipped", "cancelled"),
        ("success", "cancelled", "cancelled"),
        ("", "success", "missing"),
        (None, "success", "missing"),
        ("success", "skipped", "non_success"),
        ("unknown", "success", "unknown"),
        ("success", "bogus", "unknown"),
    ],
)
def test_partition_keeps_non_success_out_of_the_success_bucket(
    daily: object,
    validators: object,
    expected: str,
) -> None:
    assert partition_producer(daily, validators) == expected
    assert partition_bucket(expected) == (
        "success"
        if expected == "success"
        else "cancelled"
        if expected == "cancelled"
        else "diagnostics"
    )


def test_friday_schedule_keeps_weekly_skips_and_rejects_mandatory_skips() -> None:
    assert _aggregate(_results())["status"] == "success"
    forced = _aggregate(_results(), force_weekly="true")
    assert forced["status"] == "failure"
    reasons = {
        item["job"]: item["reason"]
        for item in forced["jobs"]
        if item["reason"] == "mandatory_skipped"
    }
    assert reasons["codeql"] == "mandatory_skipped"
    assert reasons["mutation"] == "mandatory_skipped"
    monday = _aggregate(_results(codeql="skipped"), dow="Mon")
    assert monday["status"] == "failure"
    sunday = _aggregate(_results(mutation="success"), dow="Sun")
    assert sunday["status"] == "success"


def test_missing_and_unknown_are_not_success_or_zero() -> None:
    missing = _aggregate(_results(tests=""))
    assert missing["status"] == "missing"
    unknown = _aggregate(_results(security="pending"))
    assert unknown["status"] == "unknown"
    assert job_duty("codeql", dow="", dom="23", month="10", force_weekly="false") == (
        "unknown"
    )
    assert (
        main(
            [
                "aggregate",
                "--event",
                "schedule",
                "--dow",
                "Fri",
                "--dom",
                "23",
                "--month",
                "10",
                "--force-weekly",
                "false",
                *[f"--result={name}={value}" for name, value in _results().items()],
            ]
        )
        == 0
    )


def test_quarter_day_does_not_follow_the_weekly_force_flag() -> None:
    skipped = _aggregate(
        _results(), dow="Thu", dom="01", month="10", force_weekly="true"
    )
    assert skipped["status"] == "failure"
    duties = {item["job"]: item["duty"] for item in skipped["jobs"]}
    assert duties["github-settings"] == "mandatory"
    assert duties["codeql"] == "mandatory"


def test_snapshot_round_trip_and_identical_rewrite(tmp_path: Path) -> None:
    raw = _raw()
    outcomes = _outcomes()
    first = _store(tmp_path, raw, outcomes)
    second = _store(tmp_path, raw, outcomes)
    assert first == second
    _seal_index(tmp_path)
    verified = verify_archive(tmp_path)
    assert verified["snapshot_count"] == 1
    assert verified["snapshots"][0]["raw_sha256"] == oracle_sha256(canonical_bytes(raw))


def test_archive_runs_appends_new_attempts_without_dropping_old_index_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _raw(run_id=11)
    second = _raw(run_id=12)
    second["created_at"] = "2026-10-10T03:00:00Z"
    selected: list[dict[str, object]] = [first]
    built_run_ids: list[object] = []

    def collect_selected(*args: object, **kwargs: object) -> list[dict[str, object]]:
        assert kwargs["include_incomplete"] is False
        return selected

    monkeypatch.setattr(
        archive_module,
        "collect_selected_runs",
        collect_selected,
    )

    def build_attempt(client: object, repository: str, run: dict[str, object]):
        built_run_ids.append(run["id"])
        raw = dict(run)
        outcomes = _outcomes()
        return raw, outcomes, _manifest(raw, outcomes)

    monkeypatch.setattr(archive_module, "build_attempt_archive", build_attempt)
    arguments = {
        "client": object(),
        "repository": "owner/repository",
        "workflow": "nightly.yml",
        "branch": "main",
        "event": "schedule",
        "limit": 40,
        "output": tmp_path,
    }
    archive_runs(**arguments)
    original_snapshot = (tmp_path / "run-11" / "attempt-1" / "raw.json").read_bytes()
    first["repository"] = {"description": "Updated repository description"}
    selected[:] = [second, first]
    report = archive_runs(**arguments)

    assert report["snapshot_count"] == 2
    assert built_run_ids == [11, 12]
    assert (
        tmp_path / "run-11" / "attempt-1" / "raw.json"
    ).read_bytes() == original_snapshot
    verified = verify_archive(tmp_path)
    assert verified["snapshot_count"] == 2
    assert [(row["run_id"], row["run_attempt"]) for row in verified["snapshots"]] == [
        (11, 1),
        (12, 1),
    ]


def test_archive_runs_waits_for_first_completed_run_before_creating_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected: list[dict[str, object]] = []

    monkeypatch.setattr(
        archive_module,
        "collect_selected_runs",
        lambda *args, **kwargs: selected,
    )

    def build_attempt(client: object, repository: str, run: dict[str, object]):
        raw = dict(run)
        outcomes = _outcomes()
        return raw, outcomes, _manifest(raw, outcomes)

    monkeypatch.setattr(archive_module, "build_attempt_archive", build_attempt)
    arguments = {
        "client": object(),
        "repository": "owner/repository",
        "workflow": "nightly.yml",
        "branch": "main",
        "event": "schedule",
        "limit": 40,
        "output": tmp_path,
    }

    assert archive_runs(**arguments)["snapshot_count"] == 0
    assert archive_runs(**arguments)["snapshot_count"] == 0
    assert not (tmp_path / "index.json").exists()

    selected.append(_raw(run_id=11))
    assert archive_runs(**arguments)["snapshot_count"] == 1
    assert verify_archive(tmp_path)["snapshot_count"] == 1


def test_existing_snapshot_is_not_overwritten(tmp_path: Path) -> None:
    _store(tmp_path, _raw(), _outcomes())
    changed = _raw()
    changed["conclusion"] = "failure"
    with pytest.raises(ArchiveError, match="already exists"):
        _store(tmp_path, changed, _outcomes())


def test_atomic_create_rejects_a_path_outside_the_archive_root(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    with pytest.raises(ValueError, match="refusing path outside"):
        _atomic_create(outside, b"{}", root=tmp_path)
    assert not outside.exists()


def test_verify_rejects_missing_archive_malformed_manifest_and_checksum(
    tmp_path: Path,
) -> None:
    with pytest.raises(ArchiveError, match="archive unavailable"):
        verify_archive(tmp_path / "missing")
    with pytest.raises(ArchiveError, match="archive index unavailable"):
        verify_archive(tmp_path)
    raw = _raw()
    outcomes = _outcomes()
    stored = _store(tmp_path, raw, outcomes)
    _seal_index(tmp_path)
    manifest_path = stored / "manifest.json"
    manifest_path.write_text("{", encoding="utf-8")
    with pytest.raises(ArchiveError, match="malformed"):
        verify_archive(tmp_path)
    _store_again = stored
    raw_path = _store_again / "raw.json"
    manifest = _manifest(raw, outcomes)
    raw_path.write_bytes(b'{"id":11}\n')
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ArchiveError, match="checksum mismatch"):
        verify_archive(tmp_path)


def test_verify_rejects_sha_attempt_and_pagination_mismatch(tmp_path: Path) -> None:
    raw = _raw()
    outcomes = _outcomes()
    stored = _store(tmp_path, raw, outcomes)
    _seal_index(tmp_path)
    manifest_path = stored / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["head_sha"] = "different"
    manifest_path.write_bytes(canonical_bytes(manifest))
    with pytest.raises(ArchiveError, match="head sha mismatch"):
        verify_archive(tmp_path)

    manifest["head_sha"] = raw["head_sha"]
    manifest_path.write_bytes(canonical_bytes(manifest))
    moved = stored.parent / "attempt-9"
    stored.rename(moved)
    with pytest.raises(ArchiveError, match="attempt mismatch"):
        verify_archive(tmp_path)

    moved.rename(stored)
    outcomes_path = stored / "outcomes.json"
    tampered = json.loads(outcomes_path.read_text(encoding="utf-8"))
    tampered["pagination"]["status"] = "complete"
    tampered["pagination"]["jobs_total_count"] = None
    outcomes_path.write_bytes(canonical_bytes(tampered))
    manifest["outcomes_sha256"] = oracle_sha256(outcomes_path.read_bytes())
    manifest["pagination_status"] = "complete"
    manifest_path.write_bytes(canonical_bytes(manifest))
    with pytest.raises(ArchiveError, match="pagination mismatch"):
        verify_archive(tmp_path)


@pytest.mark.parametrize(
    ("fetched", "total", "hit_page_cap", "expected"),
    [
        (2, 2, False, "complete"),
        (1, 3, False, "incomplete"),
        (1, None, False, "unknown"),
        (100, None, True, "incomplete"),
        (3, 2, False, "mismatch"),
    ],
)
def test_pagination_oracle_keeps_unknown_distinct(
    fetched: int,
    total: int | None,
    hit_page_cap: bool,
    expected: str,
) -> None:
    assert oracle_pagination(fetched, total, hit_page_cap=hit_page_cap) == expected


def test_mixed_history_is_an_unacceptable_window_and_blocks_the_next_stage() -> None:
    historical = assess_shadow_window(
        [
            {
                "created_at": "2026-10-09T03:00:00Z",
                "head_sha": "a" * 40,
                "pagination_status": "complete",
            },
            {
                "created_at": "2026-10-23T03:00:00Z",
                "head_sha": "b" * 40,
                "pagination_status": "unknown",
            },
        ],
        candidate_pairs=0,
        artifact_retention_days=14,
        actions_retention_cap_days=30,
        independent_review=False,
        cadence_changed_before_acceptance=True,
    )
    assert historical["status"] == "unacceptable"
    assert "mixed_tested_sha" in historical["reason_codes"]
    assert "no_parallel_candidate_arm" in historical["reason_codes"]
    assert "independent_review_absent" in historical["reason_codes"]
    assert "pagination_not_proven" in historical["reason_codes"]
    assert "success_retention_below_30" in historical["reason_codes"]
    assert "actions_retention_cap_below_90" in historical["reason_codes"]
    assert historical["independent_review"] is False
    ledger = {
        "historical_window": historical,
        "next_window": {"status": "not_started"},
    }
    with pytest.raises(ArchiveError, match="not accepted"):
        require_accepted(ledger)


def test_verify_rejects_an_indexed_snapshot_that_is_missing(tmp_path: Path) -> None:
    _store(tmp_path, _raw(run_id=11), _outcomes())
    removed = _store(tmp_path, _raw(run_id=12, head="def456"), _outcomes())
    _seal_index(tmp_path)
    shutil.rmtree(removed)
    with pytest.raises(ArchiveError, match="indexed snapshot missing"):
        verify_archive(tmp_path)


def test_verify_rejects_an_indexed_snapshot_with_a_missing_manifest(
    tmp_path: Path,
) -> None:
    stored = _store(tmp_path, _raw(run_id=11), _outcomes())
    _seal_index(tmp_path)
    (stored / "manifest.json").unlink()
    with pytest.raises(ArchiveError, match="indexed snapshot missing"):
        verify_archive(tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("head_sha", "f" * 40),
        ("created_at", "2026-10-10T03:00:00Z"),
        ("pagination_status", "incomplete"),
        ("event", "workflow_dispatch"),
        ("conclusion", "failure"),
    ],
)
def test_verify_rejects_index_metadata_that_differs_from_snapshot(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    _store(tmp_path, _raw(), _outcomes())
    _seal_index(tmp_path)
    index_path = tmp_path / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index[0][field] = value
    index_path.write_bytes(canonical_bytes(index))
    with pytest.raises(ArchiveError, match=rf"indexed metadata mismatch \({field}\)"):
        verify_archive(tmp_path)


def test_record_window_rejects_unverified_index_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(archive_module, "REPO_ROOT", tmp_path)
    _store(tmp_path, _raw(), _outcomes())
    _seal_index(tmp_path)
    index_path = tmp_path / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index[0]["head_sha"] = "f" * 40
    index_path.write_bytes(canonical_bytes(index))
    ledger_path = tmp_path / "ledger-output.json"

    result = main(
        [
            "record-window",
            "--index",
            "index.json",
            "--output",
            ledger_path.name,
            "--baseline-sha",
            "a" * 40,
            "--recorded-at",
            "2026-10-23T03:00:00Z",
            "--artifact-retention-days",
            "30",
            "--actions-retention-cap-days",
            "90",
            "--actions-permissions-http",
            "not-observed",
            "--actions-execution-observed",
            "false",
        ]
    )

    assert result == 1
    assert not ledger_path.exists()


def test_assess_shadow_window_rejects_missing_daily_attempts() -> None:
    start = datetime(2026, 10, 1, 3, tzinfo=UTC)
    runs = [
        {
            "created_at": (start + timedelta(days=day))
            .isoformat()
            .replace("+00:00", "Z"),
            "head_sha": "a" * 40,
            "pagination_status": "complete",
        }
        for day in range(15)
        if day != 7
    ]
    result = assess_shadow_window(
        runs,
        candidate_pairs=1,
        artifact_retention_days=30,
        actions_retention_cap_days=90,
        independent_review=True,
        cadence_changed_before_acceptance=False,
    )
    assert result["status"] == "unacceptable"
    assert "missing_daily_attempts" in result["reason_codes"]


def test_committed_gap_ledger_is_not_the_shadow_window() -> None:
    ledger_path = REPO_ROOT / "reports/governance/n1-shadow-window/ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    historical = ledger["historical_window"]
    assert historical["status"] == "unacceptable"
    assert "mixed_tested_sha" in historical["reason_codes"]
    assert "no_parallel_candidate_arm" in historical["reason_codes"]
    assert ledger["window_start_sha"] is None
    assert ledger["window_start_utc"] is None
    assert ledger["independent_review_record"] is None
    assert ledger["next_window"]["status"] == "not_started"
    assert ledger["durable_archive"]["minimum_days"] == 90
    assert ledger["durable_archive"]["elapsed_age_is_90_days"] is False
    assert ledger["durable_archive"]["independent_restore"] is False
    assert ledger["durable_archive"]["acceptance"] == "not_pass"
    assert (
        ledger["durable_archive"]["local_verify_archive_is_author_check_only"] is True
    )
    assert "14 full UTC days" in ledger["window_protocol"]["minimum_span"]
    assert any("Do not delete" in item for item in ledger["window_protocol"]["gaps"])
    assert (
        main(["require-accepted", "--ledger", "reports/governance/missing-ledger.json"])
        == 1
    )
