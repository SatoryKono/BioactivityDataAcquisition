"""Regression fixtures for the N1 nightly shadow archive."""

from __future__ import annotations

import inspect
import base64
import hashlib
import json
import shutil
from datetime import UTC, datetime, timedelta
from itertools import permutations
from pathlib import Path

import pytest

import scripts.engineering.ci.nightly_shadow_archive as archive_module
from scripts.engineering.ci.nightly_shadow_archive import (
    JOB_KINDS,
    PILOT_CONFIGURATION_ID,
    PILOT_RECORD_NAME,
    REPO_ROOT,
    ArchiveError,
    _atomic_create,
    _span_covers_48_minutes,
    aggregate_results,
    archive_runs,
    assess_reduced_pilot_window,
    assess_shadow_window,
    build_reduced_pilot_record,
    build_attempt_archive,
    canonical_bytes,
    job_duty,
    main,
    nightly_check_inventory,
    oracle_equivalent,
    oracle_pagination,
    oracle_sha256,
    partition_bucket,
    partition_producer,
    pilot_record_sha256,
    pilot_observation_from_archive,
    require_accepted,
    require_pilot_advance,
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


@pytest.mark.parametrize("jobs", [None, {}, [], [{}, {}]])
def test_verify_rejects_missing_or_miscounted_jobs(
    tmp_path: Path, jobs: object
) -> None:
    """Valid checksums cannot substitute for the saved job inventory."""
    outcomes = _outcomes()
    if jobs is None:
        outcomes.pop("jobs")
    else:
        outcomes["jobs"] = jobs
    _store(tmp_path, _raw(), outcomes)
    _seal_index(tmp_path)
    with pytest.raises(ArchiveError, match="pagination jobs mismatch"):
        verify_archive(tmp_path)


def _accepted_ledger() -> dict[str, object]:
    """Build synthetic acceptance fields, not real restoration evidence."""
    return {
        "historical_window": {
            "status": "complete",
            "independent_review": True,
            "reason_codes": [],
        },
        "durable_archive": {
            "acceptance": "pass",
            "independent_restore": True,
            "elapsed_age_is_90_days": True,
        },
        "independent_review_record": {"reviewer": "independent-test-reviewer"},
    }


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("historical_window", "reason_codes", None),
        ("historical_window", "reason_codes", ""),
        ("historical_window", "reason_codes", {}),
        ("historical_window", "reason_codes", ["gap"]),
        ("durable_archive", "acceptance", "not_pass"),
        ("durable_archive", "elapsed_age_is_90_days", False),
        ("durable_archive", "elapsed_age_is_90_days", 1),
    ],
)
def test_acceptance_rejects_missing_or_invalid_evidence(
    section: str, field: str, value: object
) -> None:
    """Completion flags alone cannot accept a deficient archive."""
    ledger = _accepted_ledger()
    nested = ledger[section]
    assert isinstance(nested, dict)
    nested[field] = value
    with pytest.raises(ArchiveError):
        require_accepted(ledger)
    del nested[field]
    with pytest.raises(ArchiveError):
        require_accepted(ledger)


@pytest.mark.parametrize("field", ["durable_archive"])
@pytest.mark.parametrize("value", [None, {}, "asserted", True])
def test_acceptance_requires_structured_evidence(field: str, value: object) -> None:
    """Missing and scalar evidence records must fail closed."""
    ledger = _accepted_ledger()
    ledger[field] = value
    with pytest.raises(ArchiveError):
        require_accepted(ledger)
    del ledger[field]
    with pytest.raises(ArchiveError):
        require_accepted(ledger)


def test_acceptance_does_not_require_future_window_start() -> None:
    """The acceptance barrier does not invent a future observation identity."""
    ledger = _accepted_ledger()
    assert require_accepted(ledger) is None
    ledger.update(window_start_sha=None, window_start_utc=None)
    assert require_accepted(ledger) is None


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
        artifact_retention_days=6,
        actions_retention_cap_days=30,
        independent_review=False,
        cadence_changed_before_acceptance=True,
    )
    assert historical["status"] == "unacceptable"
    assert "mixed_tested_sha" in historical["reason_codes"]
    assert "no_parallel_candidate_arm" in historical["reason_codes"]
    assert "independent_review_absent" not in historical["reason_codes"]
    assert "pagination_not_proven" in historical["reason_codes"]
    assert "success_retention_below_7" in historical["reason_codes"]
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


@pytest.mark.parametrize("index_name", ["index.json", "other-index.json"])
def test_record_window_rejects_unverified_index_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    index_name: str,
) -> None:
    monkeypatch.setattr(archive_module, "REPO_ROOT", tmp_path)
    _store(tmp_path, _raw(), _outcomes())
    _seal_index(tmp_path)
    index_path = tmp_path / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index_name == "index.json":
        index[0]["head_sha"] = "f" * 40
    index_path.write_bytes(canonical_bytes(index))
    ledger_path = tmp_path / "ledger-output.json"

    result = main(
        [
            "record-window",
            "--index",
            index_name,
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


@pytest.mark.parametrize("missing_day", [None, 7])
@pytest.mark.parametrize("retention_days", [7, 30])
def test_assess_shadow_window_rejects_missing_daily_attempts(
    missing_day, retention_days
) -> None:
    """Accept both current and historical retention when daily evidence is complete."""
    start = datetime(2026, 10, 1, 3, tzinfo=UTC)
    runs = [
        {
            "created_at": (start + timedelta(days=day))
            .isoformat()
            .replace("+00:00", "Z"),
            "head_sha": "a" * 40,
            "pagination_status": "complete",
            "event": "schedule",
        }
        for day in range(15)
        if day != missing_day
    ]
    result = assess_shadow_window(
        runs,
        candidate_pairs=1,
        artifact_retention_days=retention_days,
        actions_retention_cap_days=90,
        # P0 policy dropped independent review as an acceptance gate.
        independent_review=False,
        cadence_changed_before_acceptance=False,
    )
    if missing_day is None:
        assert result["status"] == "complete"
        assert result["reason_codes"] == []
        assert result["independent_review"] is False
    else:
        assert result["status"] == "unacceptable"
        assert result["reason_codes"] == ["missing_daily_attempts"]


@pytest.mark.parametrize(
    ("end", "ok"),
    [
        ("2026-11-03T07:59:59Z", False),
        ("2026-11-03T08:00:00Z", True),
        ("2026-11-03T03:20:00Z", False),
        ("2026-11-03T00:01:00Z", False),
    ],
)
def test_shadow_window_span_requires_full_48_wall_clock_hours(end, ok) -> None:
    from scripts.engineering.ci.nightly_shadow_archive import _span_covers_48_hours

    runs = [
        {"created_at": "2026-11-01T08:00:00Z"},
        {"created_at": end},
    ]
    assert _span_covers_48_hours(runs) is ok


def test_shadow_window_span_rejects_calendar_date_only_two_day_hop() -> None:
    from scripts.engineering.ci.nightly_shadow_archive import _span_covers_48_hours

    # UTC date delta is 2, wall-clock span is ~24h — must fail closed.
    assert not _span_covers_48_hours(
        [
            {"created_at": "2026-11-01T23:59:00Z"},
            {"created_at": "2026-11-03T00:01:00Z"},
        ]
    )


@pytest.mark.parametrize("end", ["2026-11-03T08:00:00", "2026-11-03T08:00:00Z"])
def test_shadow_window_span_rejects_timezone_naive_observations(end) -> None:
    from scripts.engineering.ci.nightly_shadow_archive import _span_covers_48_hours

    assert not _span_covers_48_hours(
        [{"created_at": "2026-11-01T08:00:00"}, {"created_at": end}]
    )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("head_sha", None, "missing_tested_sha"),
        ("head_sha", "", "missing_tested_sha"),
        ("event", "workflow_dispatch", "missing_daily_attempts"),
        ("event", None, "missing_daily_attempts"),
    ],
)
def test_shadow_window_rejects_unbound_or_manual_observation(
    field, value, reason
) -> None:
    start = datetime(2026, 10, 1, 3, tzinfo=UTC)
    runs = [
        {
            "created_at": (start + timedelta(days=day)).isoformat(),
            "head_sha": "a" * 40,
            "event": "schedule",
            "pagination_status": "complete",
        }
        for day in range(15)
    ]
    options = {
        "candidate_pairs": 1,
        "artifact_retention_days": 30,
        "actions_retention_cap_days": 90,
        "independent_review": True,
        "cadence_changed_before_acceptance": False,
    }
    assert assess_shadow_window(runs, **options)["status"] == "complete"
    runs[7][field] = value
    result = assess_shadow_window(runs, **options)
    assert result["status"] == "unacceptable"
    assert reason in result["reason_codes"]


def test_committed_gap_ledger_is_not_the_shadow_window() -> None:
    ledger_path = REPO_ROOT / "reports/governance/n1-shadow-window/ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    historical = ledger["historical_window"]
    assert historical["status"] == "unacceptable"
    assert "mixed_tested_sha" in historical["reason_codes"]
    assert "no_parallel_candidate_arm" in historical["reason_codes"]
    assert ledger["window_start_sha"] == ledger["baseline_sha"]
    assert isinstance(ledger["window_start_utc"], str)
    assert ledger["window_start_utc"]
    assert ledger["independent_review_record"] is None
    assert ledger["next_window"]["status"] == "started"
    assert ledger["durable_archive"]["minimum_days"] == 90
    assert ledger["durable_archive"]["elapsed_age_is_90_days"] is False
    assert ledger["durable_archive"]["independent_restore"] is False
    assert ledger["durable_archive"]["acceptance"] == "not_pass"
    assert (
        ledger["durable_archive"]["local_verify_archive_is_author_check_only"] is True
    )
    assert "48 wall-clock hours" in ledger["window_protocol"]["minimum_span"]
    assert ledger["next_window"]["minimum_hours"] == 48
    assert any("Do not delete" in item for item in ledger["window_protocol"]["gaps"])
    assert (
        main(["require-accepted", "--ledger", "reports/governance/missing-ledger.json"])
        == 1
    )


def test_partition_reports_current_success_retention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Producer metadata must match the seven-day successful artifact policy."""
    monkeypatch.setattr(archive_module, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    output = tmp_path / archive_module.PARTITION_NAME
    assert (
        main(
            [
                "partition",
                "--daily-outcome",
                "success",
                "--validators-outcome",
                "success",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["success_retention_days"] == 7
    assert payload["diagnostic_retention_target_days"] == 90


BASELINE_SHA = "c41cd6f7b7e4f1cb841358837fec6c6d30625106"
_SHA = "a" * 40


def _pilot_options(**overrides: object) -> dict[str, object]:
    options: dict[str, object] = {
        "configuration_id": PILOT_CONFIGURATION_ID,
        "scheduled_success_total_count": None,
        "successful_evidence_days": 30,
        "diagnostic_retention_days": 90,
        "verified_archive_days": 90,
        "actions_retention_cap_days": 90,
        "cadence_changed": False,
        "retention_reduced": False,
        "shallow_checkout": False,
        "independent_review": False,
        "independent_restore": False,
        "observation_totals": {
            name: overrides.pop(f"{name}_total_count", None)
            for name in ("failure", "cancelled", "missing", "unknown")
        },
    }
    options.update(overrides)
    return options


def _pilot_success(run_id: int, *, arm: str, created_at: str, **extra: object) -> dict:
    payload: dict[str, object] = {
        "arm": arm,
        "configuration_id": PILOT_CONFIGURATION_ID,
        "conclusion": "success",
        "created_at": created_at,
        "dom": "16",
        "dow": "Mon",
        "event": "schedule",
        "force_weekly": "false",
        "head_sha": _SHA,
        "job_conclusions": _results(),
        "month": "11",
        "run_id": run_id,
        "run_attempt": 1,
    }
    payload.update(extra)
    return payload


def test_reduced_pilot_is_not_opened_without_a_successful_scheduled_pair() -> None:
    """Zero successful scheduled Nightly runs cannot open the 48-minute window."""

    result = assess_reduced_pilot_window(
        [
            {
                "conclusion": "failure",
                "configuration_id": PILOT_CONFIGURATION_ID,
                "created_at": "2026-11-15T03:07:49Z",
                "event": "schedule",
                "head_sha": "f" * 40,
                "run_id": 43670936545,
            }
        ],
        **_pilot_options(scheduled_success_total_count=0, failure_total_count=36),
    )
    assert result["status"] == "not_opened"
    assert result["equivalence"] == "not_passed"
    assert result["sample_size_pairs"] == 0
    assert "no_suitable_successful_scheduled_nightly" in result["reason_codes"]
    assert result["counts"]["api"]["success"] == 0
    assert result["counts"]["api"]["failure"] == 36
    assert result["counts"]["sample"]["failure"] == 1
    assert result["counts"]["sample"]["success"] == 0
    assert result["n2_blocked"] is True
    assert result["independent_review"] is False


def test_unknown_success_count_is_not_recorded_as_zero() -> None:
    result = assess_reduced_pilot_window([], **_pilot_options())
    assert result["status"] == "not_opened"
    assert result["equivalence"] == "not_passed"
    assert "successful_scheduled_count_unknown" in result["reason_codes"]
    assert "no_suitable_successful_scheduled_nightly" not in result["reason_codes"]
    assert result["counts"]["api"]["success"] is None
    assert result["counts"]["api"]["missing"] is None
    assert result["counts"]["api"]["unknown"] is None


def test_reduced_pilot_rejects_synthetic_events() -> None:
    start = "2026-11-16T03:00:00Z"
    end = "2026-11-16T03:48:00Z"
    observations = [
        _pilot_success(20, arm="baseline", created_at=start, dow="Fri"),
        _pilot_success(21, arm="candidate", created_at=end, dow="Fri"),
        {
            "arm": "candidate",
            "conclusion": "success",
            "configuration_id": PILOT_CONFIGURATION_ID,
            "created_at": end,
            "event": "synthetic",
            "head_sha": _SHA,
            "run_id": 22,
            "synthetic": True,
        },
    ]
    result = assess_reduced_pilot_window(
        observations,
        **_pilot_options(scheduled_success_total_count=2),
    )
    assert result["equivalence"] == "not_passed"
    assert result["status"] == "unacceptable"
    assert "synthetic_event" in result["reason_codes"]
    assert result["counts"]["sample"]["synthetic"] == 1
    assert result["counts"]["sample"]["success"] == 2


def test_success_failure_and_cancelled_stay_distinct() -> None:
    result = assess_reduced_pilot_window(
        [
            {
                "conclusion": "failure",
                "configuration_id": PILOT_CONFIGURATION_ID,
                "created_at": "2026-11-15T03:00:00Z",
                "event": "schedule",
                "head_sha": _SHA,
                "run_id": 1,
            },
            {
                "conclusion": "cancelled",
                "configuration_id": PILOT_CONFIGURATION_ID,
                "created_at": "2026-11-15T04:00:00Z",
                "event": "schedule",
                "head_sha": _SHA,
                "run_id": 2,
            },
            {
                "conclusion": None,
                "configuration_id": PILOT_CONFIGURATION_ID,
                "created_at": "2026-11-15T05:00:00Z",
                "event": "schedule",
                "head_sha": _SHA,
                "run_id": 3,
            },
            {
                "conclusion": "unknown",
                "configuration_id": PILOT_CONFIGURATION_ID,
                "created_at": "2026-11-15T06:00:00Z",
                "event": "schedule",
                "head_sha": _SHA,
                "run_id": 4,
            },
        ],
        **_pilot_options(scheduled_success_total_count=0),
    )
    assert result["counts"]["sample"] == {
        "cancelled": 1,
        "failure": 1,
        "missing": 1,
        "skipped": 0,
        "success": 0,
        "synthetic": 0,
        "unknown": 1,
    }
    assert result["counts"]["api"]["missing"] is None
    assert result["equivalence"] == "not_passed"


def test_two_runs_do_not_replace_a_48_minute_span() -> None:
    start = "2026-11-16T03:00:00Z"
    too_soon = "2026-11-16T03:01:00Z"
    assert (
        _span_covers_48_minutes([{"created_at": start}, {"created_at": too_soon}])
        is False
    )
    assert (
        _span_covers_48_minutes(
            [{"created_at": start}, {"created_at": "2026-11-16T03:48:00Z"}]
        )
        is True
    )
    result = assess_reduced_pilot_window(
        [
            _pilot_success(30, arm="baseline", created_at=start, dow="Fri"),
            _pilot_success(31, arm="candidate", created_at=too_soon, dow="Fri"),
        ],
        **_pilot_options(scheduled_success_total_count=2),
    )
    assert result["equivalence"] == "not_passed"
    assert result["status"] == "unacceptable"
    assert "shorter_than_48_minutes" in result["reason_codes"]
    assert result["sample_size_pairs"] == 0


def test_expected_weekly_skip_can_pass_and_review_still_blocks_n2() -> None:
    result = assess_reduced_pilot_window(
        [
            _pilot_success(
                40, arm="baseline", created_at="2026-11-20T03:00:00Z", dow="Fri"
            ),
            _pilot_success(
                41,
                arm="candidate",
                created_at="2026-11-20T03:48:00Z",
                dow="Fri",
            ),
        ],
        **_pilot_options(scheduled_success_total_count=2),
    )
    assert result["status"] == "complete"
    assert result["equivalence"] == "passed"
    assert result["sample_size_pairs"] == 1
    assert result["reason_codes"] == []
    assert result["n2_blocked"] is True
    assert result["independent_review"] is False
    assert result["independent_restore"] is False


def test_mandatory_skipped_is_not_pilot_success() -> None:
    monday = _results(codeql="skipped")
    result = assess_reduced_pilot_window(
        [
            _pilot_success(
                50,
                arm="baseline",
                created_at="2026-11-16T03:00:00Z",
                job_conclusions=monday,
            ),
            _pilot_success(
                51,
                arm="candidate",
                created_at="2026-11-16T03:48:00Z",
                job_conclusions=monday,
            ),
        ],
        **_pilot_options(scheduled_success_total_count=2),
    )
    assert result["equivalence"] == "not_passed"
    assert result["status"] == "not_opened"
    assert "mandatory_skipped" in result["reason_codes"]
    forced = assess_reduced_pilot_window(
        [
            _pilot_success(
                52,
                arm="baseline",
                created_at="2026-11-20T03:00:00Z",
                dow="Fri",
                force_weekly="true",
            ),
            _pilot_success(
                53,
                arm="candidate",
                created_at="2026-11-20T03:48:00Z",
                dow="Fri",
                force_weekly="true",
            ),
        ],
        **_pilot_options(scheduled_success_total_count=2),
    )
    assert forced["equivalence"] == "not_passed"
    assert "mandatory_skipped" in forced["reason_codes"]


def test_unknown_duty_skip_stays_unknown() -> None:
    jobs = _results(codeql="skipped")
    result = assess_reduced_pilot_window(
        [
            _pilot_success(
                60,
                arm="baseline",
                created_at="2026-11-20T03:00:00Z",
                dow="",
                job_conclusions=jobs,
            )
        ],
        **_pilot_options(scheduled_success_total_count=1),
    )
    assert result["equivalence"] == "not_passed"
    assert "duty_unknown" in result["reason_codes"]
    assert result["counts"]["sample"]["success"] == 1
    assert result["status"] == "not_opened"


def test_a_run_is_not_its_own_oracle() -> None:
    result = assess_reduced_pilot_window(
        [
            _pilot_success(
                70, arm="baseline", created_at="2026-11-20T03:00:00Z", dow="Fri"
            ),
            _pilot_success(
                70, arm="candidate", created_at="2026-11-20T03:48:00Z", dow="Fri"
            ),
        ],
        **_pilot_options(scheduled_success_total_count=1),
    )
    assert result["equivalence"] == "not_passed"
    assert "run_is_own_oracle" in result["reason_codes"]
    assert result["comparable_pair_count"] == 0


@pytest.mark.parametrize(
    "failure_kind,conclusion",
    [
        ("failed_run", "failure"),
        ("weekly_job_difference", "success"),
        ("missing_conclusion", None),
        ("unknown_conclusion", "unknown"),
        ("empty_conclusion", ""),
    ],
)
def test_every_pair_is_evaluated_independently_of_input_order(
    failure_kind: str,
    conclusion: str | None,
) -> None:
    baseline = _pilot_success(
        101, arm="baseline", created_at="2026-11-20T03:00:00Z", dow="Fri"
    )
    candidate = _pilot_success(
        102, arm="candidate", created_at="2026-11-20T03:48:00Z", dow="Fri"
    )
    later = _pilot_success(
        103, arm="candidate", created_at="2026-11-20T03:47:00Z", dow="Fri"
    )
    reason = "pair_not_success"
    later["conclusion"] = conclusion
    if failure_kind == "weekly_job_difference":
        later["job_conclusions"] = _results(codeql="success")
        reason = "pair_not_equivalent"
    results = [
        assess_reduced_pilot_window(
            list(items), **_pilot_options(scheduled_success_total_count=2)
        )
        for items in permutations([baseline, candidate, later])
    ]
    assert all(result == results[0] for result in results)
    assert results[0]["status"] == "unacceptable"
    assert results[0]["equivalence"] == "not_passed"
    assert results[0]["comparable_pair_count"] == 2
    assert results[0]["sample_size_pairs"] == 0
    assert reason in results[0]["reason_codes"]


def test_pair_count_covers_all_unique_pairs() -> None:
    observations = [
        _pilot_success(run_id, arm=arm, created_at=stamp, dow="Fri")
        for run_id, arm, stamp in (
            (110, "baseline", "2026-11-20T03:00:00Z"),
            (111, "baseline", "2026-11-20T03:01:00Z"),
            (112, "candidate", "2026-11-20T03:47:00Z"),
            (113, "candidate", "2026-11-20T03:48:00Z"),
        )
    ]
    result = assess_reduced_pilot_window(
        [*observations, observations[0]],
        **_pilot_options(scheduled_success_total_count=4),
    )
    assert result["status"] == "complete"
    assert result["comparable_pair_count"] == 4
    assert result["sample_size_pairs"] == 4


def test_pilot_pairs_cannot_borrow_a_scheduled_start_from_another_sha() -> None:
    observations = [
        _pilot_success(
            401, arm="baseline", created_at="2026-11-20T03:00:00Z", dow="Fri"
        ),
        _pilot_success(
            402,
            arm="baseline",
            created_at="2026-11-20T03:01:00Z",
            dow="Fri",
            event="workflow_dispatch",
            head_sha="b" * 40,
        ),
        _pilot_success(
            403,
            arm="candidate",
            created_at="2026-11-20T03:48:00Z",
            dow="Fri",
            event="workflow_dispatch",
            head_sha="b" * 40,
        ),
    ]
    for items in permutations(observations):
        result = assess_reduced_pilot_window(
            list(items),
            **_pilot_options(
                scheduled_success_total_count=1,
                independent_review=True,
                independent_restore=True,
            ),
        )
        assert result["n2_blocked"] is True
        assert result["comparable_pair_count"] == 0
        assert result["window_start_observation"]["tested_sha"] == _SHA
        assert "no_comparable_pair" in result["reason_codes"]


def test_excluded_historical_start_does_not_poison_a_valid_window() -> None:
    observations = [
        _pilot_success(
            101, arm="baseline", created_at="2026-11-20T03:00:00Z", dow="Fri"
        ),
        _pilot_success(
            102, arm="candidate", created_at="2026-11-20T03:48:00Z", dow="Fri"
        ),
        _pilot_success(
            99, arm="baseline", created_at="2026-11-13T03:00:00Z", dow="Fri"
        ),
    ]
    results = [
        assess_reduced_pilot_window(
            list(items),
            **_pilot_options(
                scheduled_success_total_count=3,
                independent_review=True,
                independent_restore=True,
            ),
        )
        for items in permutations(observations)
    ]
    assert all(result == results[0] for result in results)
    assert results[0]["status"] == "complete"
    assert results[0]["reason_codes"] == []
    assert results[0]["comparable_pair_count"] == 1
    assert results[0]["window_start_utc"] == "2026-11-20T03:00:00Z"
    assert results[0]["n2_blocked"] is False


def test_manual_candidate_does_not_block_a_scheduled_window() -> None:
    observations = [
        _pilot_success(
            120, arm="baseline", created_at="2026-11-20T03:00:00Z", dow="Fri"
        ),
        _pilot_success(
            121,
            arm="candidate",
            created_at="2026-11-20T03:48:00Z",
            dow="Fri",
            event="workflow_dispatch",
        ),
        _pilot_success(
            122,
            arm="candidate",
            created_at="2026-11-20T02:00:00Z",
            dow="Fri",
            event="workflow_dispatch",
        ),
        _pilot_success(
            123,
            arm="candidate",
            created_at="2026-11-20T04:00:00Z",
            dow="Fri",
            event="workflow_dispatch",
        ),
    ]
    result = assess_reduced_pilot_window(
        observations, **_pilot_options(scheduled_success_total_count=1)
    )
    assert result["status"] == "complete"
    assert result["sample_size_pairs"] == 1
    assert result["reason_codes"] == []


def test_manual_backdated_and_blocking_changes_fail_closed() -> None:
    manual = assess_reduced_pilot_window(
        [
            {
                "conclusion": "success",
                "configuration_id": PILOT_CONFIGURATION_ID,
                "created_at": "2026-11-16T03:00:00Z",
                "event": "workflow_dispatch",
                "head_sha": _SHA,
                "run_id": 80,
            }
        ],
        **_pilot_options(scheduled_success_total_count=0),
    )
    assert manual["status"] == "not_opened"
    assert "manual_event_not_a_start" in manual["reason_codes"]
    assert "no_suitable_successful_scheduled_nightly" in manual["reason_codes"]

    backdated = assess_reduced_pilot_window(
        [
            _pilot_success(
                81, arm="baseline", created_at="2026-11-14T03:00:00Z", dow="Fri"
            ),
            _pilot_success(
                82, arm="candidate", created_at="2026-11-14T03:48:00Z", dow="Fri"
            ),
        ],
        **_pilot_options(scheduled_success_total_count=2),
    )
    assert backdated["status"] == "not_opened"
    assert "backdated_start" in backdated["reason_codes"]

    blocked = assess_reduced_pilot_window(
        [
            _pilot_success(
                83, arm="baseline", created_at="2026-11-20T03:00:00Z", dow="Fri"
            ),
            _pilot_success(
                84, arm="candidate", created_at="2026-11-20T03:48:00Z", dow="Fri"
            ),
        ],
        **_pilot_options(
            scheduled_success_total_count=2,
            cadence_changed=True,
            retention_reduced=True,
            shallow_checkout=True,
            successful_evidence_days=7,
        ),
    )
    assert blocked["equivalence"] == "not_passed"
    assert blocked["status"] == "unacceptable"
    assert "cadence_changed" in blocked["reason_codes"]
    assert "retention_reduced" in blocked["reason_codes"]
    assert "shallow_checkout" in blocked["reason_codes"]
    assert "success_retention_below_30" in blocked["reason_codes"]


def test_pilot_advance_blocks_on_archive_errors(tmp_path: Path) -> None:
    assessment = {
        "equivalence": "passed",
        "independent_restore": True,
        "independent_review": True,
        "n2_blocked": False,
        "status": "complete",
    }
    with pytest.raises(ArchiveError, match="archive unavailable"):
        require_pilot_advance(assessment, tmp_path / "missing")

    malformed = tmp_path / "malformed"
    stored = _store(malformed, _raw(), _outcomes())
    _seal_index(malformed)
    (stored / "manifest.json").write_text("{", encoding="utf-8")
    with pytest.raises(ArchiveError, match="malformed"):
        require_pilot_advance(assessment, malformed)

    checksum = tmp_path / "checksum"
    stored = _store(checksum, _raw(), _outcomes())
    _seal_index(checksum)
    (stored / "raw.json").write_bytes(b'{"id":11}\n')
    with pytest.raises(ArchiveError, match="checksum mismatch"):
        require_pilot_advance(assessment, checksum)

    missing = tmp_path / "missing-artifact"
    removed = _store(missing, _raw(), _outcomes())
    _seal_index(missing)
    shutil.rmtree(removed)
    with pytest.raises(ArchiveError, match="indexed snapshot missing"):
        require_pilot_advance(assessment, missing)


def test_verified_archive_still_blocks_n2_for_an_unopened_pilot(tmp_path: Path) -> None:
    _store(tmp_path, _raw(), _outcomes())
    _seal_index(tmp_path)
    assessment = assess_reduced_pilot_window(
        [],
        **_pilot_options(scheduled_success_total_count=0),
    )
    with pytest.raises(ArchiveError, match="N2 stays blocked"):
        require_pilot_advance(assessment, tmp_path)


class _PilotApiClient:
    def __init__(self) -> None:
        self.workflow = (REPO_ROOT / archive_module.WORKFLOW_PATH).read_bytes()
        self.clock_ranges = {
            130: ("2026-11-20T03:00:00Z", "2026-11-20T03:00:01Z"),
            131: ("2026-11-20T03:47:00Z", "2026-11-20T03:48:00Z"),
        }
        self.jobs = []
        for job_id, conclusion in _results().items():
            name = job_id
            if job_id == "generated-artifact-daily":
                name = "Generated artifact assertions (daily)"
            elif job_id in {
                "tests",
                "e2e",
                "security",
                "duplication",
                "import-linter",
                "zizmor",
            }:
                name = f"{job_id} / {job_id}-complete"
            self.jobs.append(
                {"name": name, "status": "completed", "conclusion": conclusion}
            )
        self.jobs.extend(
            [
                {
                    "name": "tests / Unit fast (unit-domain)",
                    "status": "completed",
                    "conclusion": "success",
                },
                {
                    "name": "tests / conditional lane",
                    "status": "completed",
                    "conclusion": "skipped",
                },
            ]
        )

    def json(self, args: list[str]) -> dict:
        if "/contents/" in args[1]:
            assert args[1].endswith(f"?ref={_SHA}")
            blob = hashlib.sha1(
                f"blob {len(self.workflow)}\0".encode() + self.workflow,
                usedforsecurity=False,
            ).hexdigest()
            return {
                "encoding": "base64",
                "content": base64.b64encode(self.workflow).decode(),
                "sha": blob,
            }
        assert "/attempts/" in args[1] and "/jobs?" in args[1]
        run_id = int(args[1].split("/runs/")[1].split("/", 1)[0])
        clock_start, clock_end = self.clock_ranges[run_id]
        jobs = [
            {
                **job,
                **(
                    {"started_at": clock_start, "completed_at": clock_end}
                    if job["conclusion"] != "skipped"
                    else {}
                ),
            }
            for job in self.jobs
        ]
        return {"jobs": jobs, "total_count": len(jobs)}


def _pilot_api_runs() -> list[dict]:
    return [
        {**_raw(run_id, head=_SHA), "created_at": stamp}
        for run_id, stamp in (
            (130, "2026-11-20T03:00:00Z"),
            (131, "2026-11-20T03:47:00Z"),
        )
    ]


def _archived_pilot_assessment(root: Path) -> dict[str, object]:
    observations = [
        pilot_observation_from_archive(root, run_id=run_id, run_attempt=1, arm=arm)
        for run_id, arm in ((130, "baseline"), (131, "candidate"))
    ]
    return assess_reduced_pilot_window(
        observations,
        **_pilot_options(
            scheduled_success_total_count=2,
            independent_review=True,
            independent_restore=True,
        ),
    )


def _archived_pilot_pair(root: Path) -> dict[str, object]:
    client = _PilotApiClient()
    for run in _pilot_api_runs():
        raw, outcomes, manifest = build_attempt_archive(
            client, "owner/repository", run, pilot=True
        )
        assert "configuration_id" not in raw
        write_snapshot(root, raw=raw, outcomes=outcomes, manifest=manifest)
    _seal_index(root)
    return _archived_pilot_assessment(root)


def test_pilot_archive_runs_binds_real_api_configuration_and_job_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _pilot_api_runs()
    monkeypatch.setattr(
        archive_module, "collect_selected_runs", lambda *args, **kwargs: runs
    )
    archive_runs(
        _PilotApiClient(),
        "owner/repository",
        workflow="nightly.yml",
        branch="main",
        event="schedule",
        limit=2,
        output=tmp_path,
        pilot=True,
    )
    assessment = _archived_pilot_assessment(tmp_path)
    assert assessment["n2_blocked"] is False
    jobs = assessment["evaluated_pairs"][0]["baseline"]["job_conclusions"]
    assert jobs["generated-artifact-daily"] == "success"
    assert jobs["tests"] == "success"
    assert (
        assessment["evaluated_pairs"][0]["baseline"]["api_job_conclusions"][
            "tests / conditional lane"
        ]
        == "skipped"
    )
    require_pilot_advance(assessment, tmp_path)


@pytest.mark.parametrize(
    "created,clock_day,dow,dom,month",
    [
        ("2026-11-16", "2026-11-17", "Tue", "17", "11"),
        ("2026-11-30", "2026-12-01", "Tue", "01", "12"),
        ("2027-01-01", "2027-01-02", "Sat", "02", "01"),
    ],
)
def test_archived_retry_calendar_comes_from_this_attempts_clock_job(
    tmp_path: Path,
    created: str,
    clock_day: str,
    dow: str,
    dom: str,
    month: str,
) -> None:
    client = _PilotApiClient()
    client.clock_ranges[130] = (f"{clock_day}T03:00:00Z", f"{clock_day}T03:00:01Z")
    run = {
        **_pilot_api_runs()[0],
        "created_at": f"{created}T03:00:00Z",
        "run_attempt": 2,
    }
    raw, outcomes, manifest = build_attempt_archive(
        client, "owner/repository", run, pilot=True
    )
    write_snapshot(tmp_path, raw=raw, outcomes=outcomes, manifest=manifest)
    _seal_index(tmp_path)
    observation = pilot_observation_from_archive(
        tmp_path, run_id=130, run_attempt=2, arm="baseline"
    )
    assert (observation["dow"], observation["dom"], observation["month"]) == (
        dow,
        dom,
        month,
    )
    assert observation["calendar_source"] == "clock_job_utc_interval"
    assert archive_module._job_block_reason(observation) is None


@pytest.mark.parametrize(
    "start,end",
    [
        (None, None),
        ("2026-11-20T23:59:59Z", "2026-11-21T00:00:01Z"),
        ("2026-11-20T03:00:01Z", "2026-11-20T03:00:00Z"),
    ],
)
def test_archived_clock_with_ambiguous_or_missing_date_stays_unknown(
    tmp_path: Path,
    start: str | None,
    end: str | None,
) -> None:
    client = _PilotApiClient()
    client.clock_ranges[130] = (start, end)
    raw, outcomes, manifest = build_attempt_archive(
        client, "owner/repository", _pilot_api_runs()[0], pilot=True
    )
    write_snapshot(tmp_path, raw=raw, outcomes=outcomes, manifest=manifest)
    _seal_index(tmp_path)
    observation = pilot_observation_from_archive(
        tmp_path, run_id=130, run_attempt=1, arm="baseline"
    )
    assert observation["calendar_source"] == "unknown"
    assert observation["dow"] is observation["dom"] is observation["month"] is None
    assert archive_module._job_block_reason(observation) == "duty_unknown"


@pytest.mark.parametrize(
    "evidence", ["late_week", "missing", "late_child", "missing_child"]
)
@pytest.mark.parametrize("attempt", [1, 2])
def test_retry_cannot_retroactively_complete_a_historical_window(
    tmp_path: Path,
    evidence: str,
    attempt: int,
) -> None:
    client = _PilotApiClient()
    if evidence == "late_week":
        client.clock_ranges = dict.fromkeys(
            (130, 131), ("2026-11-27T03:00:00Z", "2026-11-27T03:00:01Z")
        )
    elif evidence == "missing":
        client.clock_ranges = dict.fromkeys((130, 131), (None, None))
    for run in _pilot_api_runs():
        raw, outcomes, manifest = build_attempt_archive(
            client, "owner/repository", {**run, "run_attempt": attempt}, pilot=True
        )
        if evidence == "late_child":
            # Preserve clock's valid day while another executed job finishes a week later.
            outcomes["jobs"][1]["completed_at"] = "2026-11-27T03:00:01Z"
            archive_module._bind_hashes(raw, outcomes, manifest)
        elif evidence == "missing_child":
            outcomes["jobs"][1]["started_at"] = None
            archive_module._bind_hashes(raw, outcomes, manifest)
        write_snapshot(tmp_path, raw=raw, outcomes=outcomes, manifest=manifest)
    _seal_index(tmp_path)
    observations = [
        pilot_observation_from_archive(
            tmp_path, run_id=run_id, run_attempt=attempt, arm=arm
        )
        for run_id, arm in ((130, "baseline"), (131, "candidate"))
    ]
    result = assess_reduced_pilot_window(
        observations,
        **_pilot_options(
            scheduled_success_total_count=2,
            independent_review=True,
            independent_restore=True,
        ),
    )
    assert result["n2_blocked"] is True
    assert result["equivalence"] == "not_passed"
    with pytest.raises(ArchiveError, match="N2 stays blocked"):
        require_pilot_advance(result, tmp_path)


def test_retry_inside_window_requires_confirmed_execution_bounds() -> None:
    start = datetime(2026, 11, 20, 3, tzinfo=UTC)
    close = start + timedelta(minutes=48)
    observation = {
        "run_attempt": 2,
        "attempt_execution": {
            "started_at": "2026-11-20T03:01:00Z",
            "completed_at": "2026-11-20T03:47:00Z",
        },
    }
    assert (
        archive_module._attempt_execution_in_window(observation, start, close) is True
    )
    assert (
        archive_module._attempt_execution_in_window({"run_attempt": 2}, start, close)
        is False
    )
    observation["attempt_execution"]["completed_at"] = "2026-11-20T03:49:00Z"
    assert (
        archive_module._attempt_execution_in_window(observation, start, close) is False
    )


def test_archive_gate_accepts_a_retry_with_confirmed_execution_inside_window(
    tmp_path: Path,
) -> None:
    client = _PilotApiClient()
    client.clock_ranges[130] = ("2026-11-20T03:01:00Z", "2026-11-20T03:01:01Z")
    for run in _pilot_api_runs():
        run = {**run, "run_attempt": 2 if run["id"] == 130 else 1}
        raw, outcomes, manifest = build_attempt_archive(
            client, "owner/repository", run, pilot=True
        )
        write_snapshot(tmp_path, raw=raw, outcomes=outcomes, manifest=manifest)
    _seal_index(tmp_path)
    observations = [
        pilot_observation_from_archive(
            tmp_path, run_id=run_id, run_attempt=attempt, arm=arm
        )
        for run_id, attempt, arm in ((130, 2, "baseline"), (131, 1, "candidate"))
    ]
    result = assess_reduced_pilot_window(
        observations,
        **_pilot_options(
            scheduled_success_total_count=2,
            independent_review=True,
            independent_restore=True,
        ),
    )
    assert result["n2_blocked"] is False
    require_pilot_advance(result, tmp_path)


def test_attempt_execution_keeps_precision_at_the_window_boundary() -> None:
    execution = archive_module._pilot_attempt_execution(
        {
            "jobs": [
                {
                    "conclusion": "success",
                    "started_at": "2026-11-20T03:01:00Z",
                    "completed_at": "2026-11-20T03:48:00.001Z",
                }
            ]
        }
    )
    assert execution is not None
    observation = {"run_attempt": 2, "attempt_execution": execution}
    assert (
        archive_module._attempt_execution_in_window(
            observation,
            datetime(2026, 11, 20, 3, tzinfo=UTC),
            datetime(2026, 11, 20, 3, 48, tzinfo=UTC),
        )
        is False
    )


def test_pilot_advance_requires_the_evaluated_archive(tmp_path: Path) -> None:
    assessment = _archived_pilot_pair(tmp_path / "pilot")
    assert assessment["n2_blocked"] is False
    require_pilot_advance(assessment, tmp_path / "pilot")
    unrelated = tmp_path / "unrelated"
    _store(unrelated, _raw(), _outcomes())
    _seal_index(unrelated)
    assert verify_archive(unrelated)["status"] == "verified"
    with pytest.raises(
        ArchiveError, match="window start is not in the verified archive"
    ):
        require_pilot_advance(assessment, unrelated)


def test_pilot_requires_collected_configuration_instead_of_an_api_custom_field(
    tmp_path: Path,
) -> None:
    raw = {**_raw(130, head=_SHA), "configuration_id": PILOT_CONFIGURATION_ID}
    _store(tmp_path, raw, _outcomes())
    _seal_index(tmp_path)
    with pytest.raises(ArchiveError, match="configuration evidence is missing"):
        pilot_observation_from_archive(
            tmp_path, run_id=130, run_attempt=1, arm="baseline"
        )


@pytest.mark.parametrize("mutation", ["cadence", "checksum", "code_sha"])
def test_pilot_collector_rejects_unverified_workflow_configuration(
    mutation: str,
) -> None:
    client = _PilotApiClient()
    if mutation == "cadence":
        client.workflow = client.workflow.replace(b"dow == 'Mon'", b"dow == 'Fri'", 1)
    if mutation == "cadence":
        with pytest.raises(ArchiveError, match="cadence drifted"):
            build_attempt_archive(
                client, "owner/repository", _pilot_api_runs()[0], pilot=True
            )
        return
    raw, outcomes, _ = build_attempt_archive(
        client, "owner/repository", _pilot_api_runs()[0], pilot=True
    )
    configuration = outcomes["pilot_configuration"]
    configuration[
        "workflow_blob_sha" if mutation == "checksum" else "workflow_code_sha"
    ] = "0" * 40
    with pytest.raises(ArchiveError, match="checksum mismatch|identity mismatch"):
        archive_module._pilot_configuration_jobs(raw, outcomes)


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "unknown", "skipped"])
def test_pilot_reusable_job_results_fail_closed(conclusion: str) -> None:
    client = _PilotApiClient()
    for job in client.jobs:
        if job["name"].startswith("tests / "):
            job["conclusion"] = conclusion
    raw, outcomes, _ = build_attempt_archive(
        client, "owner/repository", _pilot_api_runs()[0], pilot=True
    )
    jobs = archive_module._pilot_configuration_jobs(raw, outcomes)
    normalized, _ = archive_module._pilot_archive_job_results(outcomes, jobs)
    observation = _pilot_success(
        130,
        arm="baseline",
        created_at="2026-11-20T03:00:00Z",
        dow="Fri",
        job_conclusions=normalized,
    )
    assert archive_module._job_block_reason(observation) is not None


def test_pilot_equivalence_preserves_reusable_child_outcome_differences(
    tmp_path: Path,
) -> None:
    assessment = _archived_pilot_pair(tmp_path)
    pair = assessment["evaluated_pairs"][0]
    pair["candidate"]["api_job_conclusions"]["tests / conditional lane"] = "success"
    reasons = []
    assert (
        archive_module._pair_equivalence(pair["baseline"], pair["candidate"], reasons)
        == "not_passed"
    )
    assert "pair_not_equivalent" in reasons


@pytest.mark.parametrize("change", ["unknown_name", "duplicate_name", "incomplete"])
def test_pilot_job_mapping_rejects_ambiguous_or_incomplete_evidence(
    change: str,
) -> None:
    client = _PilotApiClient()
    if change == "unknown_name":
        client.jobs[0]["name"] = "unrecognized job"
    elif change == "duplicate_name":
        client.jobs.append(dict(client.jobs[0]))
    else:
        client.jobs[0]["status"] = "in_progress"
    raw, outcomes, _ = build_attempt_archive(
        client, "owner/repository", _pilot_api_runs()[0], pilot=True
    )
    jobs = archive_module._pilot_configuration_jobs(raw, outcomes)
    with pytest.raises(
        ArchiveError, match="identity is ambiguous or unknown|duplicate or incomplete"
    ):
        archive_module._pilot_archive_job_results(outcomes, jobs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("head_sha", "b" * 40),
        ("event", "workflow_dispatch"),
        ("created_at", "2026-11-20T03:01:00Z"),
    ],
)
def test_pilot_advance_rechecks_the_archived_window_start(
    tmp_path: Path, field: str, value: str
) -> None:
    assessment = _archived_pilot_pair(tmp_path)
    assessment["window_start_observation"][field] = value
    with pytest.raises(
        ArchiveError, match="window start is not in the verified archive"
    ):
        require_pilot_advance(assessment, tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_attempt", 2),
        ("head_sha", "b" * 40),
        ("tested_sha", "b" * 40),
        ("configuration_id", "other"),
        ("raw_sha256", "0" * 64),
        ("outcomes_sha256", "0" * 64),
        ("job_conclusions", {"clock": "failure"}),
        ("attempt_execution", {"started_at": "2026-11-27T03:00:00Z"}),
    ],
)
def test_pilot_advance_rejects_mismatched_evidence(
    tmp_path: Path, field: str, value: object
) -> None:
    assessment = _archived_pilot_pair(tmp_path)
    assessment["evaluated_pairs"][0]["candidate"][field] = value
    with pytest.raises(ArchiveError):
        require_pilot_advance(assessment, tmp_path)


@pytest.mark.parametrize(
    "job,old,new",
    [
        ("codeql", "'Mon'", "'Fri'"),
        ("codeql", "'Mon'", "'M on'"),
        ("codeql", "'Mon'", "'Mon '"),
        ("codeql", "'Mon'", "' Mon'"),
        ("scorecard", "'Mon'", "'Fri'"),
        ("branch-hygiene", "'Mon'", "'Fri'"),
        ("mutation", "'Sun'", "'Fri'"),
        ("github-settings", "dom == '01'", "dom == '02'"),
        ("github-settings", "month == '04'", "month == '05'"),
    ],
)
def test_inventory_rejects_cadence_drift_in_each_job(
    tmp_path: Path, job: str, old: str, new: str
) -> None:
    text = (REPO_ROOT / ".github/workflows/nightly.yml").read_text(encoding="utf-8")
    start = text.index(f"\n  {job}:\n")
    # Bound the replacement to the selected top-level job, preserving other jobs.
    following = [
        offset
        for offset in range(start + 1, len(text))
        if text.startswith("\n  ", offset) and not text.startswith("\n   ", offset)
    ]
    end = following[0] if following else len(text)
    block = text[start:end]
    assert old in block
    changed = text[:start] + block.replace(old, new, 1) + text[end:]
    workflow = tmp_path / ".github/workflows"
    workflow.mkdir(parents=True)
    (workflow / "nightly.yml").write_text(changed, encoding="utf-8")
    with pytest.raises(ArchiveError, match=f"cadence drifted: {job}"):
        nightly_check_inventory(tmp_path)


@pytest.mark.parametrize("location", ["condition", "job", "root"])
def test_nightly_workflow_rejects_duplicate_yaml_keys(location: str) -> None:
    text = (REPO_ROOT / ".github/workflows/nightly.yml").read_text(encoding="utf-8")
    if location == "condition":
        text = text.replace("  codeql:\n", "  codeql:\n    if: false\n", 1)
    elif location == "job":
        text += "\n  codeql:\n    if: needs.clock.outputs.dow == 'Mon'\n"
    else:
        text += "\npermissions:\n  contents: read\n"
    with pytest.raises(ArchiveError, match="malformed nightly workflow"):
        archive_module._validated_workflow_jobs(text)


def test_nightly_job_condition_keeps_literal_spaces_and_escaped_quotes() -> None:
    normalize = archive_module._normalized_job_condition
    assert normalize(" ${{ needs.clock.outputs.dow == 'Mon' }} ") == normalize(
        "needs.clock.outputs.dow=='Mon'"
    )
    assert normalize(" 'a '' b' == 'a '' b' ") == "'a '' b'=='a '' b'"
    assert normalize("'M on'") != normalize("'Mon'")
    for invalid in ("${{ true", "true }}", "'Mon"):
        with pytest.raises(ArchiveError):
            normalize(invalid)


def test_pilot_record_reports_observed_retention_below_the_floor() -> None:
    inventory = nightly_check_inventory()
    assert inventory["workflow_success_artifact_retention_days"] == 7
    record = build_reduced_pilot_record(baseline_sha=BASELINE_SHA, inventory=inventory)
    assert "success_retention_below_30" in record["assessment"]["reason_codes"]
    assert record["status"] == "not_opened"
    assert record["retention_floors"]["successful_evidence_days"] == 30
    assert record["n2_blocked"] is True


def test_nightly_inventory_matches_workflow_and_fails_on_drift(tmp_path: Path) -> None:
    inventory = nightly_check_inventory()
    assert {row["name"] for row in inventory["jobs"]} == set(JOB_KINDS)
    assert set(inventory["security_and_external_jobs"]) == {
        "branch-hygiene",
        "codeql",
        "github-settings",
        "scorecard",
        "security",
        "zizmor",
    }
    by_name = {row["name"]: row for row in inventory["jobs"]}
    assert by_name["security"]["schedule_kind"] == "security_daily"
    assert by_name["security"]["observation_class"] == "external_state_security"
    assert by_name["codeql"]["cadence"] == "weekly_monday"
    assert by_name["tests"]["observation_class"] == "deterministic"
    assert inventory["fetch_depth"] == 0
    assert inventory["shallow_checkout"] is False
    assert inventory["cron"] == "0 3 * * *"
    assert inventory["owner"] == "CI"
    assert inventory["reviewers"] == [
        "security",
        "test-subject-owner",
        "evidence-keeper",
    ]
    assert "generated_artifact_checks.py" in " ".join(
        inventory["generated_artifact_checks"]
    )
    workflow = tmp_path / ".github/workflows"
    workflow.mkdir(parents=True)
    (workflow / "nightly.yml").write_text(
        "name: Nightly\njobs:\n  clock:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    checks = tmp_path / "scripts/engineering/ci"
    checks.mkdir(parents=True)
    (checks / "generated_artifact_checks.py").write_text(
        "daily validators\n",
        encoding="utf-8",
    )
    with pytest.raises(ArchiveError, match="drifted"):
        nightly_check_inventory(tmp_path)


def test_historical_ledger_and_archive_bytes_match_pinned_baseline() -> None:
    fixture = Path(__file__).with_name("fixtures") / "n1_historical_baseline.json"
    baseline = json.loads(fixture.read_text(encoding="utf-8"))
    assert baseline["baseline_sha"] == BASELINE_SHA
    archive = REPO_ROOT / "reports/governance/n1-shadow-window/unacceptable"
    paths = [REPO_ROOT / "reports/governance/n1-shadow-window/ledger.json"]
    paths.extend(path for path in archive.rglob("*") if path.is_file())
    actual = {
        path.relative_to(REPO_ROOT).as_posix(): oracle_sha256(path.read_bytes())
        for path in paths
    }
    assert actual == baseline["files"]


def test_committed_pilot_record_is_not_opened(tmp_path: Path) -> None:
    record_path = REPO_ROOT / "reports/governance/n1-shadow-window" / PILOT_RECORD_NAME
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record_path.read_bytes().endswith(b"\n")
    assert record["schema_version"] == 1
    assert record["decision_date"] == "2026-11-15"
    assert record["duration_minutes"] == 48
    assert record["configuration_id"] == PILOT_CONFIGURATION_ID
    assert record["baseline_sha"] == BASELINE_SHA
    assert record["status"] == "not_opened"
    assert record["equivalence"] == "not_passed"
    assert "no_suitable_successful_scheduled_nightly" in record["reason_codes"]
    assert record["sample"]["sample_size_pairs"] == 0
    assert record["sample"]["successful_scheduled_nightly_total_count"] == 0
    assert "48 minutes" in record["sample"]["definition"]
    assert record["replaces_parent_acceptance"] is False
    assert record["n2_blocked"] is True
    assert record["independent_review"] is False
    assert record["independent_restore"] is False
    assert record["shallow_checkout"] is False
    assert record["cadence_changed"] is False
    assert record["retention_changed"] is False
    assert record["retention_floors"]["successful_evidence_days"] == 30
    assert record["retention_floors"]["verified_archive_days"] == 90
    assert record["api_counts"]["missing"] is None
    assert record["api_counts"]["unknown"] is None
    assert record["sha256"] == pilot_record_sha256(record)
    rebuilt = build_reduced_pilot_record(
        baseline_sha=BASELINE_SHA,
        inventory=nightly_check_inventory(),
    )
    assert record_path.read_bytes() == canonical_bytes(rebuilt)
    cited = {item["run_id"]: item for item in record["cited_failure_runs"]}
    assert cited[43670936545]["created_at"] == "2026-11-15T03:07:49Z"
    assert cited[43670936545]["head_sha"] == "f6f924bd6d3cf362e14a20206bd611179ca800a3"
    assert cited[43549950171]["created_at"] == "2026-11-14T03:07:22Z"
    assert cited[43356852695]["created_at"] == "2026-11-13T03:07:44Z"
    limitations = "\n".join(record["limitations"])
    assert "total_count=0" in limitations
    assert "#12349" in limitations
    assert "Cadence, retention, and shallow checkout are unchanged." in limitations
    ledger = json.loads(
        (REPO_ROOT / "reports/governance/n1-shadow-window/ledger.json").read_text(
            encoding="utf-8"
        )
    )
    assert ledger["baseline_sha"] != record["baseline_sha"]
    assert ledger["historical_window"]["candidate_pairs"] == 0
    copied = main(
        [
            "record-pilot",
            "--baseline-sha",
            BASELINE_SHA,
            "--output",
            f"reports/governance/n1-shadow-window/{PILOT_RECORD_NAME}",
        ]
    )
    assert copied == 0
    refused = main(
        [
            "record-pilot",
            "--baseline-sha",
            BASELINE_SHA,
            "--output",
            "reports/governance/n1-shadow-window/other.json",
        ]
    )
    assert refused == 1
