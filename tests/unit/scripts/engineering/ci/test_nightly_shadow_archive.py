"""Regression fixtures for the N1 nightly shadow archive."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.engineering.ci.nightly_shadow_archive import (
    JOB_KINDS,
    ArchiveError,
    aggregate_results,
    assess_shadow_window,
    canonical_bytes,
    job_duty,
    main,
    oracle_equivalent,
    oracle_pagination,
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
    verified = verify_archive(tmp_path)
    assert verified["snapshot_count"] == 1
    assert verified["snapshots"][0]["raw_sha256"] == oracle_sha256(canonical_bytes(raw))


def test_existing_snapshot_is_not_overwritten(tmp_path: Path) -> None:
    _store(tmp_path, _raw(), _outcomes())
    changed = _raw()
    changed["conclusion"] = "failure"
    with pytest.raises(ArchiveError, match="already exists"):
        _store(tmp_path, changed, _outcomes())


def test_verify_rejects_missing_archive_malformed_manifest_and_checksum(
    tmp_path: Path,
) -> None:
    with pytest.raises(ArchiveError, match="archive unavailable"):
        verify_archive(tmp_path / "missing")
    with pytest.raises(ArchiveError, match="archive unavailable"):
        verify_archive(tmp_path)
    raw = _raw()
    outcomes = _outcomes()
    stored = _store(tmp_path, raw, outcomes)
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
    assert (
        main(["require-accepted", "--ledger", "reports/governance/missing-ledger.json"])
        == 1
    )
