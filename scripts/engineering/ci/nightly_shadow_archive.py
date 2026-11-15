"""Nightly shadow evidence for N1.

The schedule classifier and the oracle are separate. The oracle recomputes
checksums, pagination, and outcome equality from stored bytes. It does not
decide which weekly job should run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

REPO_ROOT = Path(__file__).resolve().parents[3]
if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.engineering.ci.actions_timing_common import (
    JsonGitHubClient,
    collect_jobs_observation,
    collect_selected_runs,
    pull_request_shas,
)
from scripts.engineering.common.repo_paths import (
    ensure_path_within_root,
    rebuild_confined_path,
    resolve_cli_path,
    write_bytes_confined,
)
from scripts.engineering.repo.github_settings_review import (
    GitHubReviewError,
    ReadOnlyGitHubClient,
)

SCHEMA_VERSION = 1
ARCHIVE_INDEX_NAME = "index.json"
PARTITION_NAME = "generated-artifact-daily-partition.json"
WORKFLOW_PATH = ".github/workflows/nightly.yml"
ACTIONS_RETENTION_CAP_DAYS = 90
SUCCESS_RETENTION_DAYS = 7
DIAGNOSTIC_RETENTION_DAYS = 90
PILOT_DURATION_MINUTES = 48
PILOT_DECISION_DATE = "2026-11-15"
PILOT_DECISION_UTC = "2026-11-15T00:00:00Z"
PILOT_CONFIGURATION_ID = "daily-deterministic-plus-existing-weekly-security"
PILOT_SUCCESS_RETENTION_FLOOR_DAYS = 30
PILOT_DIAGNOSTIC_RETENTION_FLOOR_DAYS = 90
PILOT_VERIFIED_ARCHIVE_FLOOR_DAYS = 90
PILOT_RECORD_NAME = "pilot-48min.json"
PILOT_ISSUE = 12362
PARENT_ACCEPTANCE_ISSUE = 12349
_SYNTHETIC_EVENTS = frozenset({"synthetic", "fabricated"})
_EXTERNAL_OBSERVATION = frozenset({"external_state", "external_state_security"})
REQUIRED_EXTERNAL_JOBS = (
    "security",
    "zizmor",
    "codeql",
    "scorecard",
    "branch-hygiene",
    "github-settings",
)
RUN_ID_LABEL = "run id"
RUN_ATTEMPT_LABEL = "run attempt"
UTC_OFFSET_SUFFIX = "+00:00"
WEEKDAYS = frozenset({"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"})
QUARTER_MONTHS = frozenset({"01", "04", "07", "10"})
JOB_KINDS: dict[str, str] = {
    "clock": "clock",
    "tests": "deterministic",
    "e2e": "deterministic",
    "duplication": "deterministic",
    "import-linter": "deterministic",
    "generated-artifact-daily": "deterministic",
    "security": "security_daily",
    "zizmor": "security_daily",
    "codeql": "weekly_monday",
    "scorecard": "weekly_monday",
    "branch-hygiene": "weekly_monday",
    "mutation": "weekly_sunday",
    "github-settings": "quarterly",
}
CHECK_CLASS: dict[str, str] = {
    "clock": "clock",
    "tests": "deterministic",
    "e2e": "deterministic",
    "duplication": "deterministic",
    "import-linter": "deterministic",
    "generated-artifact-daily": "deterministic",
    "mutation": "deterministic",
    "security": "external_state_security",
    "zizmor": "external_state_security",
    "codeql": "external_state_security",
    "scorecard": "external_state_security",
    "branch-hygiene": "external_state",
    "github-settings": "external_state",
}
_CADENCE_LABEL = {
    "clock": "every_scheduled_nightly",
    "deterministic": "every_scheduled_nightly",
    "security_daily": "every_scheduled_nightly",
    "weekly_monday": "weekly_monday",
    "weekly_sunday": "weekly_sunday",
    "quarterly": "quarterly",
}
_WORKFLOW_DRIFT_SNIPPETS = (
    'cron: "0 3 * * *"',
    "fetch-depth: 0",
    "scripts.engineering.ci.generated_artifact_checks",
    "needs.clock.outputs.dow == 'Mon'",
    "needs.clock.outputs.dow == 'Sun'",
    "retention-days: 7",
    "retention-days: 90",
    "if-no-files-found: warn",
)
_SUCCESS_TOKENS = frozenset({"success"})
_FAILURE_TOKENS = frozenset({"failure"})
_CANCELLED_TOKENS = frozenset({"cancelled"})
_SKIPPED_TOKENS = frozenset({"skipped"})
_KNOWN_RESULTS = _SUCCESS_TOKENS | _FAILURE_TOKENS | _CANCELLED_TOKENS | _SKIPPED_TOKENS


class ArchiveError(ValueError):
    """Fail closed when an evidence snapshot cannot be trusted."""


def canonical_bytes(payload: object) -> bytes:
    """Serialize JSON with a stable key order and a trailing newline."""

    text = json.dumps(
        payload,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    )
    return (text + "\n").encode("utf-8")


def oracle_sha256(payload: bytes) -> str:
    """Return the SHA-256 of exact bytes. This is not a job scheduler."""

    return hashlib.sha256(payload).hexdigest()


def oracle_pagination(fetched: object, total: object, *, hit_page_cap: object) -> str:
    """Classify raw page counts without treating unknown as success or zero."""

    if total is None:
        return "incomplete" if hit_page_cap is True else "unknown"
    if isinstance(fetched, bool) or isinstance(total, bool):
        return "unknown"
    if not isinstance(fetched, int) or not isinstance(total, int):
        return "unknown"
    if fetched < 0 or total < 0:
        return "unknown"
    if hit_page_cap is True or fetched < total:
        return "incomplete"
    if fetched == total:
        return "complete"
    return "mismatch"


def oracle_equivalent(
    left: Mapping[str, object],
    right: Mapping[str, object],
    *,
    job_names: Sequence[str],
) -> dict[str, Any]:
    """Compare stored conclusions. Missing stays missing and is not success."""

    mismatches: list[dict[str, object]] = []
    for name in job_names:
        left_value = left.get(name, "missing")
        right_value = right.get(name, "missing")
        if left_value != right_value or left_value in (None, "", "missing"):
            mismatches.append(
                {
                    "job": name,
                    "left": left_value,
                    "right": right_value,
                }
            )
    return {
        "equivalent": not mismatches,
        "mismatches": mismatches,
    }


def partition_producer(daily: object, validators: object) -> str:
    """Separate producer success from every other outcome before upload."""

    observed = (daily, validators)
    if any(_is_blank(item) for item in observed):
        return "missing"
    if any(item in _CANCELLED_TOKENS for item in observed):
        return "cancelled"
    if any(item == "unknown" for item in observed):
        return "unknown"
    if any(item in _FAILURE_TOKENS or item in _SKIPPED_TOKENS for item in observed):
        return "non_success"
    if all(item in _SUCCESS_TOKENS for item in observed):
        return "success"
    return "unknown"


def partition_bucket(kind: str) -> str:
    """Map a producer class onto an upload bucket. Only success is success."""

    if kind == "success":
        return "success"
    if kind == "cancelled":
        return "cancelled"
    return "diagnostics"


def parse_force(value: object) -> bool | None:
    """Parse a workflow input. Unexpected text stays unknown."""

    if value is True:
        return True
    if value is False or value is None:
        return False
    if not isinstance(value, str):
        return None
    if value in {"", "false", "False"}:
        return False
    if value in {"true", "True"}:
        return True
    return None


def job_duty(
    name: str,
    *,
    dow: object,
    dom: object,
    month: object,
    force_weekly: object,
) -> str:
    """Return whether one inventoried job is mandatory for this event."""

    kind = JOB_KINDS.get(name)
    if kind is None:
        return "unknown"
    if kind in {"clock", "deterministic", "security_daily"}:
        return "mandatory"
    force = parse_force(force_weekly)
    weekday = dow if isinstance(dow, str) and dow in WEEKDAYS else None
    if kind == "weekly_monday":
        return _weekly_duty(weekday == "Mon", force, weekday is not None)
    if kind == "weekly_sunday":
        return _weekly_duty(weekday == "Sun", force, weekday is not None)
    if kind == "quarterly":
        return _quarterly_duty(dom, month)
    return "unknown"


def judge_job(result: object, duty: str) -> dict[str, str]:
    """Judge one job. A mandatory skip is not a pass."""

    token = result if isinstance(result, str) else ""
    if token == "":
        return {"status": "missing", "reason": "result_missing"}
    if token not in _KNOWN_RESULTS:
        return {"status": "unknown", "reason": "result_unknown"}
    if token in _FAILURE_TOKENS:
        return {"status": "failure", "reason": "job_failure"}
    if token in _CANCELLED_TOKENS:
        return {"status": "cancelled", "reason": "job_cancelled"}
    if duty == "unknown":
        if token in _SKIPPED_TOKENS:
            return {"status": "unknown", "reason": "duty_unknown"}
        if token in _SUCCESS_TOKENS:
            return {"status": "success", "reason": "ran"}
        return {"status": "unknown", "reason": "duty_unknown"}
    if duty == "not_mandatory" and token in _SKIPPED_TOKENS:
        return {"status": "success", "reason": "expected_skip"}
    if duty == "mandatory" and token in _SKIPPED_TOKENS:
        return {"status": "failure", "reason": "mandatory_skipped"}
    if token in _SUCCESS_TOKENS:
        return {"status": "success", "reason": "ran"}
    return {"status": "unknown", "reason": "result_unknown"}


def aggregate_results(
    results: Mapping[str, object],
    *,
    dow: object,
    dom: object,
    month: object,
    force_weekly: object,
) -> dict[str, Any]:
    """Fail closed unless every mandatory job actually succeeded."""

    jobs: list[dict[str, str]] = []
    for name in JOB_KINDS:
        duty = job_duty(
            name,
            dow=dow,
            dom=dom,
            month=month,
            force_weekly=force_weekly,
        )
        judged = judge_job(results.get(name, ""), duty)
        jobs.append({"job": name, "duty": duty, **judged})
    return {
        "schema_version": SCHEMA_VERSION,
        "status": _overall_status([item["status"] for item in jobs]),
        "jobs": jobs,
    }


def assess_shadow_window(
    runs: Sequence[Mapping[str, object]],
    *,
    candidate_pairs: int,
    artifact_retention_days: int,
    actions_retention_cap_days: int,
    independent_review: bool,
    cadence_changed_before_acceptance: bool,
) -> dict[str, Any]:
    """Decide whether a collected run set is an acceptable N1 window."""

    reasons: list[str] = []
    shas = {
        str(run.get("head_sha"))
        for run in runs
        if isinstance(run.get("head_sha"), str) and run.get("head_sha")
    }
    if not runs:
        reasons.append("empty_window")
    elif len(shas) != 1:
        reasons.append("mixed_tested_sha")
    if any(
        not isinstance(run.get("head_sha"), str) or not run["head_sha"].strip()
        for run in runs
    ):
        reasons.append("missing_tested_sha")
    if candidate_pairs < 1:
        reasons.append("no_parallel_candidate_arm")
    reasons.extend(_window_observation_reason_codes(runs))
    if artifact_retention_days < SUCCESS_RETENTION_DAYS:
        reasons.append(f"success_retention_below_{SUCCESS_RETENTION_DAYS}")
    if actions_retention_cap_days < DIAGNOSTIC_RETENTION_DAYS:
        reasons.append("actions_retention_cap_below_90")
    if any(run.get("pagination_status") != "complete" for run in runs):
        reasons.append("pagination_not_proven")
    # Independent review is not a P0 acceptance gate for the 48-hour window.
    # The flag is still recorded for ledger transparency.
    if cadence_changed_before_acceptance:
        reasons.append("cadence_changed_before_shadow_acceptance")
    created = _created_bounds(runs)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "unacceptable" if reasons else "complete",
        "reason_codes": sorted(set(reasons)),
        "run_count": len(runs),
        "unique_head_sha_count": len(shas),
        "candidate_pairs": candidate_pairs,
        "utc_start": created[0],
        "utc_end": created[1],
        "independent_review": independent_review,
    }


def write_snapshot(
    root: Path,
    *,
    raw: Mapping[str, Any],
    outcomes: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> Path:
    """Write one attempt. An existing different snapshot is an error."""

    run_id = _positive_int(raw.get("id"), RUN_ID_LABEL)
    attempt = _positive_int(raw.get("run_attempt"), RUN_ATTEMPT_LABEL)
    destination = ensure_path_within_root(
        root / f"run-{run_id}" / f"attempt-{attempt}",
        root,
    )
    files = {
        "raw.json": canonical_bytes(raw),
        "outcomes.json": canonical_bytes(outcomes),
        "manifest.json": canonical_bytes(manifest),
    }
    existing = [destination / name for name in files if (destination / name).exists()]
    if existing and not _same_snapshot(destination, files):
        raise ArchiveError(f"snapshot already exists: {destination}")
    if existing:
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        _atomic_create(destination / name, payload, root=root)
    return destination


def verify_archive(root: Path) -> dict[str, Any]:
    """Recompute checksums and require every indexed snapshot to exist."""

    if not root.is_dir():
        raise ArchiveError(f"archive unavailable: {root}")
    index = _load_index(root / ARCHIVE_INDEX_NAME)
    manifests = sorted(root.glob("run-*/attempt-*/manifest.json"))
    checked = [_verify_one(path) for path in manifests]
    _require_index_coverage(index, checked)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "verified",
        "snapshot_count": len(checked),
        "snapshots": checked,
    }


def require_accepted(ledger: Mapping[str, Any]) -> None:
    """Block the next stage until the recorded window is independently accepted."""

    historical = ledger.get("historical_window")
    if not isinstance(historical, Mapping):
        raise ArchiveError("ledger is missing historical_window")
    if historical.get("status") != "complete":
        raise ArchiveError("shadow window is not accepted")
    reasons = historical.get("reason_codes")
    if not isinstance(reasons, list) or reasons:
        raise ArchiveError("shadow window still has gap reasons")
    archive = ledger.get("durable_archive")
    if not isinstance(archive, Mapping):
        raise ArchiveError("ledger is missing durable_archive")
    if archive.get("acceptance") != "pass":
        raise ArchiveError("durable archive is not accepted")
    # 90-day durable aging remains; independent restore/review were dropped for P0.
    if archive.get("elapsed_age_is_90_days") is not True:
        raise ArchiveError("durable archive has not aged 90 days")


def build_attempt_archive(
    client: JsonGitHubClient,
    repository: str,
    run: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Collect one attempt through the shared timing collector."""

    run_id = _positive_int(run.get("id"), RUN_ID_LABEL)
    attempt = _positive_int(run.get("run_attempt"), RUN_ATTEMPT_LABEL)
    jobs, observation = collect_jobs_observation(
        client,
        repository,
        run_id,
        attempt,
    )
    raw = dict(run.get("raw_api") if isinstance(run.get("raw_api"), Mapping) else run)
    raw["run_attempt"] = attempt
    pagination_status = oracle_pagination(
        observation["jobs_fetched"],
        observation["jobs_total_count"],
        hit_page_cap=observation["hit_page_cap"],
    )
    outcomes = {
        "schema_version": SCHEMA_VERSION,
        "jobs": [
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
            }
            for job in jobs
        ],
        "pagination": {
            "jobs_fetched": observation["jobs_fetched"],
            "jobs_total_count": observation["jobs_total_count"],
            "pages_fetched": observation["pages_fetched"],
            "hit_page_cap": observation["hit_page_cap"],
            "status": pagination_status,
        },
    }
    base_sha, tested_sha = pull_request_shas(dict(raw))
    head_sha = raw.get("head_sha") if isinstance(raw.get("head_sha"), str) else None
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "workflow_path": raw.get("path") or WORKFLOW_PATH,
        "workflow_code_sha": head_sha,
        "workflow_code_sha_source": "head_sha" if head_sha else "missing",
        "action_sha": None,
        "action_sha_status": "missing",
        "head_sha": head_sha,
        "base_sha": base_sha,
        "tested_sha": tested_sha,
        "run_id": run_id,
        "run_attempt": attempt,
        "event": raw.get("event"),
        "conclusion": raw.get("conclusion"),
        "timestamps": {
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
            "run_started_at": raw.get("run_started_at"),
        },
        "pagination_status": pagination_status,
    }
    manifest["raw_sha256"] = oracle_sha256(canonical_bytes(raw))
    manifest["outcomes_sha256"] = oracle_sha256(canonical_bytes(outcomes))
    return raw, outcomes, manifest


def archive_runs(
    client: JsonGitHubClient,
    repository: str,
    *,
    workflow: str,
    branch: str | None,
    event: str | None,
    limit: int,
    output: Path,
) -> dict[str, Any]:
    """Write immutable attempt snapshots and a derived index."""

    runs = collect_selected_runs(
        client,
        repository,
        workflow=workflow,
        branch=branch,
        event=event,
        limit=limit,
        run_ids=(),
        # Attempt snapshots are immutable. Do not archive a run until GitHub
        # reports its final conclusion, or a later collection would conflict
        # with the already stored snapshot for the same run/attempt.
        include_incomplete=False,
        workflow_runs_endpoint=_workflow_endpoint,
    )
    index_path = ensure_path_within_root(output / ARCHIVE_INDEX_NAME, output)
    index, previous_index_bytes = _existing_archive_index(output, index_path)
    index, snapshots = _collect_archive_snapshots(client, repository, runs, index)
    _persist_archive_snapshots(
        output, index_path, index, previous_index_bytes, snapshots
    )
    return {"snapshot_count": len(index), "index": str(index_path)}


def _existing_archive_index(
    output: Path,
    index_path: Path,
) -> tuple[list[dict[str, Any]], bytes | None]:
    if index_path.exists():
        verify_archive(output)
        return _load_index(index_path), index_path.read_bytes()
    if list(output.glob("run-*/attempt-*/manifest.json")):
        raise ArchiveError("archive snapshots exist without an index")
    return [], None


def _collect_archive_snapshots(
    client: JsonGitHubClient,
    repository: str,
    runs: Sequence[Mapping[str, Any]],
    existing_index: Sequence[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]],
]:
    index_by_key: dict[tuple[int, int], dict[str, Any]] = {}
    for row in existing_index:
        key = _snapshot_key(row)
        if key in index_by_key:
            raise ArchiveError(f"duplicate snapshot in archive index: {key}")
        index_by_key[key] = row
    snapshots: list[tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]] = []
    for run in runs:
        key = (
            _positive_int(run.get("id"), RUN_ID_LABEL),
            _positive_int(run.get("run_attempt"), RUN_ATTEMPT_LABEL),
        )
        # The existing archive was verified before collection. Keep its original
        # immutable snapshot: nested API metadata (such as repository.description)
        # can change even when this completed attempt has not changed.
        if key in index_by_key:
            continue
        raw, outcomes, manifest = build_attempt_archive(client, repository, run)
        _bind_hashes(raw, outcomes, manifest)
        row = _index_row(manifest)
        key = _snapshot_key(row)
        previous = index_by_key.get(key)
        if previous is not None and previous != row:
            raise ArchiveError(
                f"indexed snapshot changed: run {key[0]} attempt {key[1]}"
            )
        index_by_key[key] = row
        snapshots.append((raw, outcomes, manifest))
    return list(index_by_key.values()), snapshots


def _persist_archive_snapshots(
    output: Path,
    index_path: Path,
    index: Sequence[Mapping[str, Any]],
    previous_index_bytes: bytes | None,
    snapshots: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]],
) -> None:
    # An index is proof that at least one immutable attempt was archived.  Do
    # not create an empty index on the initial poll: verify_archive() correctly
    # rejects empty indexes, so materialising one here would make every later
    # archive update fail before a completed run can arrive.
    if previous_index_bytes is None and not index and not snapshots:
        return
    payload = canonical_bytes(index)
    new_directories: list[Path] = []
    try:
        for raw, outcomes, manifest in snapshots:
            run_id = _positive_int(raw.get("id"), RUN_ID_LABEL)
            attempt = _positive_int(raw.get("run_attempt"), RUN_ATTEMPT_LABEL)
            destination = ensure_path_within_root(
                output / f"run-{run_id}" / f"attempt-{attempt}", output
            )
            if not destination.exists():
                new_directories.append(destination)
            write_snapshot(output, raw=raw, outcomes=outcomes, manifest=manifest)
        _write_archive_index(index_path, payload, previous_index_bytes, output)
    except BaseException:
        for directory in reversed(new_directories):
            if directory.exists():
                shutil.rmtree(directory)
        raise


def _write_archive_index(
    index_path: Path,
    payload: bytes,
    previous_index_bytes: bytes | None,
    root: Path,
) -> None:
    if index_path.exists():
        if index_path.read_bytes() != previous_index_bytes:
            raise ArchiveError(f"index changed during archive update: {index_path}")
        if payload != previous_index_bytes:
            write_bytes_confined(index_path, payload, root=root)
        return
    _atomic_create(index_path, payload, root=root)


def _bind_hashes(
    raw: Mapping[str, Any],
    outcomes: Mapping[str, Any],
    manifest: dict[str, Any],
) -> None:
    manifest["raw_sha256"] = oracle_sha256(canonical_bytes(raw))
    manifest["outcomes_sha256"] = oracle_sha256(canonical_bytes(outcomes))


def _index_row(manifest: Mapping[str, Any]) -> dict[str, Any]:
    timestamps = manifest.get("timestamps")
    created_at = None
    if isinstance(timestamps, Mapping):
        created_at = timestamps.get("created_at")
    return {
        "run_id": manifest.get("run_id"),
        "run_attempt": manifest.get("run_attempt"),
        "head_sha": manifest.get("head_sha"),
        "event": manifest.get("event"),
        "conclusion": manifest.get("conclusion"),
        "created_at": created_at,
        "pagination_status": manifest.get("pagination_status"),
        "raw_sha256": manifest.get("raw_sha256"),
    }


def _weekly_duty(on_day: bool, force: bool | None, dow_known: bool) -> str:
    if force is True:
        return "mandatory"
    if force is None or not dow_known:
        return "unknown"
    if on_day:
        return "mandatory"
    return "not_mandatory"


def _quarterly_duty(dom: object, month: object) -> str:
    if not isinstance(dom, str) or not isinstance(month, str):
        return "unknown"
    if not dom or not month:
        return "unknown"
    if dom == "01" and month in QUARTER_MONTHS:
        return "mandatory"
    return "not_mandatory"


def _overall_status(statuses: Sequence[str]) -> str:
    if any(item == "failure" for item in statuses):
        return "failure"
    if any(item == "cancelled" for item in statuses):
        return "cancelled"
    if any(item == "missing" for item in statuses):
        return "missing"
    if any(item == "unknown" for item in statuses):
        return "unknown"
    if statuses and all(item == "success" for item in statuses):
        return "success"
    return "unknown"


def _is_blank(value: object) -> bool:
    return value is None or value == ""


def _span_covers_48_hours(runs: Sequence[Mapping[str, object]]) -> bool:
    """True when the wall-clock span is at least 48 hours in UTC."""
    start, end = _created_bounds(runs)
    if start is None or end is None:
        return False
    try:
        opened = datetime.fromisoformat(start.replace("Z", UTC_OFFSET_SUFFIX))
        closed = datetime.fromisoformat(end.replace("Z", UTC_OFFSET_SUFFIX))
    except ValueError:
        return False
    if opened.tzinfo is None or closed.tzinfo is None:
        return False
    opened_utc = opened.astimezone(UTC)
    closed_utc = closed.astimezone(UTC)
    return (closed_utc - opened_utc) >= timedelta(hours=48)


def _window_observation_reason_codes(
    runs: Sequence[Mapping[str, object]],
) -> list[str]:
    reasons: list[str] = []
    scheduled = [run for run in runs if run.get("event") == "schedule"]
    if not _span_covers_48_hours(scheduled):
        reasons.append("shorter_than_48_hours")
    if len(scheduled) != len(runs) or _missing_utc_days(scheduled):
        reasons.append("missing_daily_attempts")
    return reasons


def _missing_utc_days(runs: Sequence[Mapping[str, object]]) -> list[str]:
    days: set[date] = set()
    for run in runs:
        created_at = run.get("created_at")
        if not isinstance(created_at, str):
            return ["unknown"]
        try:
            stamp = datetime.fromisoformat(created_at.replace("Z", UTC_OFFSET_SUFFIX))
        except ValueError:
            return ["unknown"]
        if stamp.tzinfo is None:
            return ["unknown"]
        days.add(stamp.astimezone(UTC).date())
    if not days:
        return ["unknown"]
    missing: list[str] = []
    current = min(days)
    end = max(days)
    while current <= end:
        if current not in days:
            missing.append(current.isoformat())
        current += timedelta(days=1)
    return missing


def _created_bounds(
    runs: Sequence[Mapping[str, object]],
) -> tuple[str | None, str | None]:
    stamps = [
        str(run.get("created_at"))
        for run in runs
        if isinstance(run.get("created_at"), str) and run.get("created_at")
    ]
    if len(stamps) != len(runs) or not stamps:
        return None, None
    ordered = sorted(stamps)
    return ordered[0], ordered[-1]


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ArchiveError(f"invalid {label}")
    return value


def _same_snapshot(destination: Path, files: Mapping[str, bytes]) -> bool:
    for name, payload in files.items():
        path = destination / name
        if not path.is_file() or path.read_bytes() != payload:
            return False
    return True


def _atomic_create(path: Path, payload: bytes, *, root: Path) -> None:
    safe = rebuild_confined_path(path, root=root)
    if safe.exists():
        raise ArchiveError(f"refusing to overwrite {safe}")
    temporary = rebuild_confined_path(safe.with_suffix(safe.suffix + ".tmp"), root=root)
    write_bytes_confined(temporary, payload, root=root)
    try:
        os.replace(temporary, safe)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def _load_index(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ArchiveError(f"archive index unavailable: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"malformed archive index: {path}") from exc
    if not isinstance(payload, list) or not payload:
        raise ArchiveError(f"archive index unavailable: {path}")
    rows: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            raise ArchiveError(f"malformed archive index: {path}")
        rows.append(row)
    return rows


def _snapshot_key(row: Mapping[str, Any]) -> tuple[int, int]:
    return (
        _positive_int(row.get("run_id"), "indexed run id"),
        _positive_int(row.get("run_attempt"), "indexed attempt"),
    )


def _require_index_coverage(
    index: Sequence[Mapping[str, Any]],
    checked: Sequence[Mapping[str, Any]],
) -> None:
    found: dict[tuple[int, int], Mapping[str, Any]] = {}
    for row in checked:
        key = _snapshot_key(row)
        if key in found:
            raise ArchiveError(f"duplicate snapshot: {key}")
        found[key] = row
    indexed: set[tuple[int, int]] = set()
    for row in index:
        key = _snapshot_key(row)
        snapshot = found.get(key)
        if snapshot is None:
            raise ArchiveError(
                f"indexed snapshot missing: run {key[0]} attempt {key[1]}"
            )
        for field in (
            "head_sha",
            "event",
            "conclusion",
            "created_at",
            "pagination_status",
            "raw_sha256",
        ):
            if snapshot.get(field) != row.get(field):
                raise ArchiveError(
                    f"indexed metadata mismatch ({field}): "
                    f"run {key[0]} attempt {key[1]}"
                )
        indexed.add(key)
    extras = set(found) - indexed
    if extras:
        raise ArchiveError(f"snapshot is not in the archive index: {sorted(extras)}")


def _verify_one(manifest_path: Path) -> dict[str, Any]:
    destination = manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_bytes = (destination / "raw.json").read_bytes()
        outcomes_bytes = (destination / "outcomes.json").read_bytes()
        raw = json.loads(raw_bytes.decode("utf-8"))
        outcomes = json.loads(outcomes_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"malformed snapshot: {destination}") from exc
    if not isinstance(manifest, dict) or not isinstance(raw, dict):
        raise ArchiveError(f"malformed snapshot: {destination}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ArchiveError(f"schema mismatch: {destination}")
    if oracle_sha256(raw_bytes) != manifest.get("raw_sha256"):
        raise ArchiveError(f"checksum mismatch: {destination / 'raw.json'}")
    if oracle_sha256(outcomes_bytes) != manifest.get("outcomes_sha256"):
        raise ArchiveError(f"checksum mismatch: {destination / 'outcomes.json'}")
    _verify_identity(destination, manifest, raw, outcomes)
    return _index_row(manifest)


def _verify_identity(
    destination: Path,
    manifest: Mapping[str, Any],
    raw: Mapping[str, Any],
    outcomes: Mapping[str, Any],
) -> None:
    attempt_name = destination.name.removeprefix("attempt-")
    run_name = destination.parent.name.removeprefix("run-")
    if str(manifest.get("run_id")) != run_name or str(raw.get("id")) != run_name:
        raise ArchiveError(f"run id mismatch: {destination}")
    if (
        str(manifest.get("run_attempt")) != attempt_name
        or str(raw.get("run_attempt")) != attempt_name
    ):
        raise ArchiveError(f"attempt mismatch: {destination}")
    if manifest.get("head_sha") != raw.get("head_sha"):
        raise ArchiveError(f"head sha mismatch: {destination}")
    timestamps = manifest.get("timestamps")
    if (
        not isinstance(timestamps, Mapping)
        or timestamps.get("created_at") != raw.get("created_at")
        or manifest.get("event") != raw.get("event")
        or manifest.get("conclusion") != raw.get("conclusion")
    ):
        raise ArchiveError(f"run metadata mismatch: {destination}")
    pagination = outcomes.get("pagination") if isinstance(outcomes, dict) else None
    if not isinstance(pagination, dict):
        raise ArchiveError(f"pagination missing: {destination}")
    jobs = outcomes.get("jobs")
    fetched = pagination.get("jobs_fetched")
    if not isinstance(jobs, list) or type(fetched) is not int or len(jobs) != fetched:
        raise ArchiveError(f"pagination jobs mismatch: {destination}")
    status = oracle_pagination(
        pagination.get("jobs_fetched"),
        pagination.get("jobs_total_count"),
        hit_page_cap=pagination.get("hit_page_cap"),
    )
    if status != pagination.get("status") or status != manifest.get(
        "pagination_status"
    ):
        raise ArchiveError(f"pagination mismatch: {destination}")


def _parse_utc(value: object) -> datetime | None:
    """Parse a timezone-aware UTC timestamp. Naive text stays unknown."""

    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", UTC_OFFSET_SUFFIX))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp.astimezone(UTC)


def _is_synthetic_observation(observation: Mapping[str, object]) -> bool:
    if observation.get("synthetic") is True:
        return True
    event = observation.get("event")
    return isinstance(event, str) and event in _SYNTHETIC_EVENTS


def _observation_sha(observation: Mapping[str, object]) -> str | None:
    for key in ("tested_sha", "head_sha"):
        value = observation.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _observation_run_id(observation: Mapping[str, object]) -> int | None:
    value = observation.get("run_id")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _conclusion_name(observation: Mapping[str, object]) -> str:
    """Map one conclusion. Blank and unknown stay distinct from success."""

    if _is_synthetic_observation(observation):
        return "synthetic"
    conclusion = observation.get("conclusion")
    if conclusion is None or conclusion == "" or conclusion == "missing":
        return "missing"
    if not isinstance(conclusion, str):
        return "unknown"
    if conclusion in _SUCCESS_TOKENS:
        return "success"
    if conclusion in _FAILURE_TOKENS:
        return "failure"
    if conclusion in _CANCELLED_TOKENS:
        return "cancelled"
    if conclusion in _SKIPPED_TOKENS:
        return "skipped"
    return "unknown"


def _job_block_reason(observation: Mapping[str, object]) -> str | None:
    """Return why job evidence cannot count as success. None means no block."""

    results = observation.get("job_conclusions")
    if results is None:
        return None
    if not isinstance(results, Mapping) or not results:
        return "outcomes_missing"
    force = observation["force_weekly"] if "force_weekly" in observation else False
    blocked: str | None = None
    for name, result in results.items():
        if not isinstance(name, str):
            return "outcomes_missing"
        duty = job_duty(
            name,
            dow=observation.get("dow"),
            dom=observation.get("dom"),
            month=observation.get("month"),
            force_weekly=force,
        )
        judged = judge_job(result, duty)
        if judged["reason"] == "mandatory_skipped":
            return "mandatory_skipped"
        if judged["status"] != "success" and blocked is None:
            blocked = judged["reason"]
    return blocked


def _sample_counts(
    observations: Sequence[Mapping[str, object]],
) -> dict[str, int]:
    counts = {
        "success": 0,
        "failure": 0,
        "cancelled": 0,
        "missing": 0,
        "unknown": 0,
        "skipped": 0,
        "synthetic": 0,
    }
    for observation in observations:
        bucket = _conclusion_name(observation)
        if bucket not in counts:
            bucket = "unknown"
        counts[bucket] += 1
    return counts


def _span_covers_48_minutes(runs: Sequence[Mapping[str, object]]) -> bool:
    """True when the wall-clock span is at least 48 minutes.

    Two runs do not satisfy this by themselves. The clock does.
    """

    start, end = _created_bounds(runs)
    if start is None or end is None:
        return False
    opened = _parse_utc(start)
    closed = _parse_utc(end)
    if opened is None or closed is None:
        return False
    return (closed - opened) >= timedelta(minutes=PILOT_DURATION_MINUTES)


def _pilot_duration_elapsed(
    start: datetime,
    observations: Sequence[Mapping[str, object]],
) -> bool:
    """True when a non-synthetic stamp reaches start plus 48 minutes."""

    latest = start
    seen = False
    for observation in observations:
        if _is_synthetic_observation(observation):
            continue
        stamp = _parse_utc(observation.get("created_at"))
        if stamp is None or stamp < start:
            continue
        seen = True
        if stamp > latest:
            latest = stamp
    if not seen:
        return False
    return (latest - start) >= timedelta(minutes=PILOT_DURATION_MINUTES)


def _inside_pilot_window(
    observation: Mapping[str, object],
    *,
    configuration_id: str,
    start: datetime,
    close: datetime,
) -> bool:
    if _is_synthetic_observation(observation):
        return False
    if observation.get("configuration_id") != configuration_id:
        return False
    stamp = _parse_utc(observation.get("created_at"))
    if stamp is None or stamp < start or stamp > close:
        return False
    return _observation_run_id(observation) is not None


def _find_comparable_pair(
    observations: Sequence[Mapping[str, object]],
    *,
    configuration_id: str,
    start: datetime,
    close: datetime,
) -> tuple[Mapping[str, object] | None, Mapping[str, object] | None, bool]:
    """Return one baseline/candidate pair. The same run id is not a pair."""

    baselines: list[Mapping[str, object]] = []
    candidates: list[Mapping[str, object]] = []
    for observation in observations:
        if not _inside_pilot_window(
            observation,
            configuration_id=configuration_id,
            start=start,
            close=close,
        ):
            continue
        arm = observation.get("arm")
        if arm == "baseline":
            baselines.append(observation)
        elif arm == "candidate":
            candidates.append(observation)
    self_oracle = False
    for left in baselines:
        left_id = _observation_run_id(left)
        left_sha = _observation_sha(left)
        if left_id is None or left_sha is None:
            continue
        if _conclusion_name(left) in {"missing", "unknown", "synthetic"}:
            continue
        for right in candidates:
            right_id = _observation_run_id(right)
            right_sha = _observation_sha(right)
            if right_id is None or right_sha is None:
                continue
            if _conclusion_name(right) in {"missing", "unknown", "synthetic"}:
                continue
            if left_id == right_id:
                self_oracle = True
                continue
            if left_sha != right_sha:
                continue
            return left, right, self_oracle
    return None, None, self_oracle


def _retention_reason_codes(
    *,
    successful_evidence_days: int,
    diagnostic_retention_days: int,
    verified_archive_days: int,
    actions_retention_cap_days: int,
    retention_reduced: bool,
) -> list[str]:
    reasons: list[str] = []
    if retention_reduced:
        reasons.append("retention_reduced")
    if successful_evidence_days < PILOT_SUCCESS_RETENTION_FLOOR_DAYS:
        reasons.append(f"success_retention_below_{PILOT_SUCCESS_RETENTION_FLOOR_DAYS}")
    if diagnostic_retention_days < PILOT_DIAGNOSTIC_RETENTION_FLOOR_DAYS:
        reasons.append(
            f"diagnostic_retention_below_{PILOT_DIAGNOSTIC_RETENTION_FLOOR_DAYS}"
        )
    if verified_archive_days < PILOT_VERIFIED_ARCHIVE_FLOOR_DAYS:
        reasons.append(
            f"verified_archive_retention_below_{PILOT_VERIFIED_ARCHIVE_FLOOR_DAYS}"
        )
    if actions_retention_cap_days < ACTIONS_RETENTION_CAP_DAYS:
        reasons.append("actions_retention_cap_below_90")
    return reasons


def _suitable_scheduled_successes(
    observations: Sequence[Mapping[str, object]],
    *,
    configuration_id: str,
    reasons: list[str],
) -> list[Mapping[str, object]]:
    """Keep only post-decision scheduled successes. Failures stay out."""

    decision = _parse_utc(PILOT_DECISION_UTC)
    if decision is None:
        raise ArchiveError("pilot decision instant is not UTC")
    suitable: list[Mapping[str, object]] = []
    for observation in observations:
        if _is_synthetic_observation(observation):
            reasons.append("synthetic_event")
            continue
        event = observation.get("event")
        conclusion = observation.get("conclusion")
        if event == "workflow_dispatch" and conclusion == "success":
            reasons.append("manual_event_not_a_start")
            continue
        if event != "schedule" or conclusion != "success":
            continue
        if observation.get("configuration_id") != configuration_id:
            reasons.append("configuration_mismatch")
            continue
        block = _job_block_reason(observation)
        if block is not None:
            reasons.append(block)
            continue
        if _observation_sha(observation) is None:
            reasons.append("missing_tested_sha")
            continue
        if _observation_run_id(observation) is None:
            reasons.append("missing_run_id")
            continue
        stamp = _parse_utc(observation.get("created_at"))
        if stamp is None:
            reasons.append("created_at_unknown")
            continue
        if stamp < decision:
            reasons.append("backdated_start")
            continue
        suitable.append(observation)
    return suitable


def _pair_equivalence(
    left: Mapping[str, object],
    right: Mapping[str, object],
    reasons: list[str],
) -> str:
    """Compare stored job conclusions. A mandatory skip is not success."""

    if left.get("conclusion") != "success" or right.get("conclusion") != "success":
        reasons.append("pair_not_success")
        return "not_passed"
    left_jobs = left.get("job_conclusions")
    right_jobs = right.get("job_conclusions")
    if not isinstance(left_jobs, Mapping) or not isinstance(right_jobs, Mapping):
        reasons.append("outcomes_missing")
        return "not_passed"
    if _job_block_reason(left) is not None or _job_block_reason(right) is not None:
        reasons.append("mandatory_or_unknown_job")
        return "not_passed"
    names = sorted(set(JOB_KINDS) | set(left_jobs) | set(right_jobs))
    compared = oracle_equivalent(left_jobs, right_jobs, job_names=names)
    if compared["equivalent"] is True:
        return "passed"
    reasons.append("pair_not_equivalent")
    return "not_passed"


def assess_reduced_pilot_window(
    observations: Sequence[Mapping[str, object]],
    *,
    configuration_id: str,
    scheduled_success_total_count: int | None,
    successful_evidence_days: int,
    diagnostic_retention_days: int,
    verified_archive_days: int,
    actions_retention_cap_days: int,
    cadence_changed: bool,
    retention_reduced: bool,
    shallow_checkout: bool,
    independent_review: bool,
    independent_restore: bool,
    failure_total_count: int | None = None,
    cancelled_total_count: int | None = None,
    missing_total_count: int | None = None,
    unknown_total_count: int | None = None,
) -> dict[str, Any]:
    """Judge the 48-minute pilot. This is not the 48-hour historical judge."""

    reasons: list[str] = []
    if cadence_changed:
        reasons.append("cadence_changed")
    if shallow_checkout:
        reasons.append("shallow_checkout")
    reasons.extend(
        _retention_reason_codes(
            successful_evidence_days=successful_evidence_days,
            diagnostic_retention_days=diagnostic_retention_days,
            verified_archive_days=verified_archive_days,
            actions_retention_cap_days=actions_retention_cap_days,
            retention_reduced=retention_reduced,
        )
    )
    api_success = scheduled_success_total_count
    if isinstance(api_success, bool) or (
        api_success is not None
        and (not isinstance(api_success, int) or api_success < 0)
    ):
        reasons.append("successful_scheduled_count_unknown")
        api_success = None
    suitable = _suitable_scheduled_successes(
        observations,
        configuration_id=configuration_id,
        reasons=reasons,
    )
    if api_success == 0:
        reasons.append("no_suitable_successful_scheduled_nightly")
        if suitable:
            reasons.append("success_count_contradiction")
    elif api_success is None and not suitable:
        reasons.append("successful_scheduled_count_unknown")
    elif isinstance(api_success, int) and api_success > 0 and not suitable:
        reasons.append("successful_scheduled_observations_missing")

    window_start: str | None = None
    window_end: str | None = None
    comparable_pair_count = 0
    sample_size_pairs = 0
    equivalence = "not_passed"
    opened = bool(suitable) and "success_count_contradiction" not in reasons
    if api_success == 0:
        opened = False
    if opened:
        start_obs = min(
            suitable,
            key=lambda item: (
                _parse_utc(item.get("created_at")) or datetime.max.replace(tzinfo=UTC),
                _observation_run_id(item) or 0,
            ),
        )
        start_at = _parse_utc(start_obs.get("created_at"))
        if start_at is None:
            reasons.append("created_at_unknown")
            opened = False
        else:
            close_at = start_at + timedelta(minutes=PILOT_DURATION_MINUTES)
            window_start = start_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            window_end = close_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            elapsed = _pilot_duration_elapsed(start_at, observations)
            if not elapsed:
                reasons.append("shorter_than_48_minutes")
            left, right, self_oracle = _find_comparable_pair(
                observations,
                configuration_id=configuration_id,
                start=start_at,
                close=close_at,
            )
            if self_oracle:
                reasons.append("run_is_own_oracle")
            if left is None or right is None:
                reasons.append("no_comparable_pair")
            else:
                comparable_pair_count = 1
                if elapsed and "synthetic_event" not in reasons:
                    equivalence = _pair_equivalence(left, right, reasons)
    else:
        reasons.append("no_comparable_pair")

    if not opened:
        status = "not_opened"
        equivalence = "not_passed"
    elif equivalence == "passed" and not reasons:
        status = "complete"
        sample_size_pairs = comparable_pair_count
    else:
        status = "unacceptable"
        equivalence = "not_passed"
    n2_blocked = not (
        independent_review is True
        and independent_restore is True
        and status == "complete"
        and equivalence == "passed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_date": PILOT_DECISION_DATE,
        "duration_minutes": PILOT_DURATION_MINUTES,
        "configuration_id": configuration_id,
        "status": status,
        "equivalence": equivalence,
        "reason_codes": sorted(set(reasons)),
        "window_start_utc": window_start,
        "window_end_utc": window_end,
        "comparable_pair_count": comparable_pair_count,
        "sample_size_pairs": sample_size_pairs,
        "counts": {
            "api": {
                "success": api_success,
                "failure": failure_total_count,
                "cancelled": cancelled_total_count,
                "missing": missing_total_count,
                "unknown": unknown_total_count,
            },
            "sample": _sample_counts(observations),
        },
        "independent_review": independent_review,
        "independent_restore": independent_restore,
        "n2_blocked": n2_blocked,
        "cancellation_upload": "best_effort",
        "cadence_changed": cadence_changed,
        "retention_reduced": retention_reduced,
        "shallow_checkout": shallow_checkout,
    }


def _workflow_job_names(text: str) -> list[str]:
    names: list[str] = []
    in_jobs = False
    for line in text.splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line and not line.startswith(" "):
            break
        if (
            line.startswith("  ")
            and not line.startswith("   ")
            and line.rstrip().endswith(":")
        ):
            names.append(line.strip()[:-1])
    return names


def _called_workflow_paths(text: str) -> list[str]:
    prefix = "uses: ./.github/workflows/"
    found: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(prefix):
            continue
        relative = ".github/workflows/" + stripped.removeprefix(prefix).split()[0]
        if relative not in found:
            found.append(relative)
    return found


def nightly_check_inventory(repo_root: Path | None = None) -> dict[str, Any]:
    """Classify nightly jobs and fail when the workflow inventory drifts."""

    root = REPO_ROOT if repo_root is None else repo_root
    workflow_path = root / WORKFLOW_PATH
    if not workflow_path.is_file():
        raise ArchiveError(f"nightly workflow unavailable: {workflow_path}")
    text = workflow_path.read_text(encoding="utf-8")
    job_names = _workflow_job_names(text)
    if set(job_names) != set(JOB_KINDS) or set(CHECK_CLASS) != set(JOB_KINDS):
        raise ArchiveError(
            "JOB_KINDS drifted from nightly.yml: "
            f"workflow={sorted(job_names)} kinds={sorted(JOB_KINDS)}"
        )
    for snippet in _WORKFLOW_DRIFT_SNIPPETS:
        if snippet not in text:
            raise ArchiveError(f"nightly workflow drifted: missing {snippet}")
    called = _called_workflow_paths(text)
    if not called:
        raise ArchiveError("nightly.yml calls no workflows")
    for relative in called:
        if not (root / relative).is_file():
            raise ArchiveError(f"called workflow missing: {relative}")
    check_dir = root / "scripts/engineering/ci"
    check_paths = sorted(
        path.relative_to(root).as_posix()
        for path in check_dir.glob("generated_artifact_checks*")
        if path.is_file()
    )
    if not check_paths:
        raise ArchiveError("generated_artifact_checks sources are missing")
    joined = "\n".join(
        (root / relative).read_text(encoding="utf-8") for relative in check_paths
    )
    for mode in ("daily", "validators"):
        if mode not in joined:
            raise ArchiveError(f"generated_artifact_checks missing mode {mode}")
    missing_external = [
        name for name in REQUIRED_EXTERNAL_JOBS if name not in job_names
    ]
    if missing_external:
        raise ArchiveError(
            f"security or external check dropped: {sorted(missing_external)}"
        )
    rows = []
    for name in job_names:
        kind = JOB_KINDS[name]
        rows.append(
            {
                "name": name,
                "schedule_kind": kind,
                "observation_class": CHECK_CLASS[name],
                "cadence": _CADENCE_LABEL[kind],
            }
        )
    external = [
        name for name, klass in CHECK_CLASS.items() if klass in _EXTERNAL_OBSERVATION
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_path": WORKFLOW_PATH,
        "owner": "CI",
        "reviewers": [
            "security",
            "test-subject-owner",
            "evidence-keeper",
        ],
        "jobs": rows,
        "called_workflows": called,
        "generated_artifact_checks": check_paths,
        "generated_artifact_modes": ["daily", "validators"],
        "cron": "0 3 * * *",
        "fetch_depth": 0,
        "shallow_checkout": False,
        "security_and_external_jobs": sorted(external),
        "cancellation_upload": "best_effort",
        "workflow_success_artifact_retention_days": 7,
        "workflow_diagnostic_artifact_retention_days": 90,
    }


def verified_scheduled_nightly_facts() -> dict[str, Any]:
    """Actions API facts re-verified on 2026-11-15. Failures are not a start."""

    return {
        "workflow": "nightly.yml",
        "branch": "main",
        "event": "schedule",
        "successful_total_count": 0,
        "failure_total_count": 36,
        "cancelled_total_count": 1,
        "missing_total_count": None,
        "unknown_total_count": None,
        "actions_permissions_http": "403",
        "actions_permissions_source": (
            "historical ledger observation; not re-probed and not changed"
        ),
        "cited_failure_runs": [
            {
                "run_id": 43670936545,
                "run_attempt": 1,
                "created_at": "2026-11-15T03:07:49Z",
                "head_sha": "f6f924bd6d3cf362e14a20206bd611179ca800a3",
                "event": "schedule",
                "conclusion": "failure",
                "branch": "main",
                "configuration_id": PILOT_CONFIGURATION_ID,
            },
            {
                "run_id": 43549950171,
                "run_attempt": 1,
                "created_at": "2026-11-14T03:07:22Z",
                "head_sha": "f6f924bd6d3cf362e14a20206bd611179ca800a3",
                "event": "schedule",
                "conclusion": "failure",
                "branch": "main",
                "configuration_id": PILOT_CONFIGURATION_ID,
            },
            {
                "run_id": 43356852695,
                "run_attempt": 1,
                "created_at": "2026-11-13T03:07:44Z",
                "head_sha": "2657f30e8adaf04c0cb58ed38118da235b6a4b51",
                "event": "schedule",
                "conclusion": "failure",
                "branch": "main",
                "configuration_id": PILOT_CONFIGURATION_ID,
            },
        ],
        "cited_cancelled_run": {
            "run_id": 40175268711,
            "run_attempt": 1,
            "created_at": "2026-10-25T08:05:34Z",
            "head_sha": "af5036c3d0ea68b556dd0f7053ab75f85585d871",
            "event": "schedule",
            "conclusion": "cancelled",
            "branch": "main",
            "configuration_id": PILOT_CONFIGURATION_ID,
        },
    }


def _pilot_limitations(facts: Mapping[str, Any]) -> list[str]:
    failures = facts["cited_failure_runs"]
    if not isinstance(failures, Sequence) or len(failures) < 3:
        raise ArchiveError("pilot facts are missing cited failure runs")
    first, second, third = failures[0], failures[1], failures[2]
    if not all(isinstance(item, Mapping) for item in (first, second, third)):
        raise ArchiveError("pilot facts are missing cited failure runs")
    cancelled = facts["cited_cancelled_run"]
    if not isinstance(cancelled, Mapping):
        raise ArchiveError("pilot facts are missing the cited cancelled run")
    return [
        (
            "Zero successful scheduled Nightly runs on main "
            "(event=schedule, conclusion=success, "
            f"total_count={facts['successful_total_count']}). "
            "The 48-minute window is not open and equivalence is not passed."
        ),
        (
            "Cited scheduled failures are not the window start: "
            f"{first['run_id']} at {first['created_at']} "
            f"head {first['head_sha']}; "
            f"{second['run_id']} at {second['created_at']}; "
            f"{third['run_id']} at {third['created_at']}."
        ),
        (f"The pilot does not replace acceptance of #{PARENT_ACCEPTANCE_ISSUE}."),
        "Cadence, retention, and shallow checkout are unchanged.",
        (
            "No synthetic events were substituted. "
            "The committed gap ledger is not the shadow window."
        ),
        (
            "Successful evidence floor is 30 days, failed or cancelled "
            "diagnostics floor is 90 days, verified archive floor is 90 days, "
            "and the Actions cap is 90 days. nightly.yml success artifact "
            "retention remains 7 days and was not retuned. Actions permissions "
            "were not changed (historical observation 403)."
        ),
        (
            "Cancelled scheduled total_count is "
            f"{facts['cancelled_total_count']} "
            f"(run {cancelled['run_id']}) and is not success and not a window "
            "start. Missing and unknown API counts were not observed and stay "
            "null, not zero."
        ),
    ]


def _require_commit_sha(value: str) -> None:
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise ArchiveError("baseline sha must be a full lowercase git sha")


def pilot_record_sha256(record: Mapping[str, Any]) -> str:
    """Hash the canonical record without its own sha256 field."""

    body = {key: value for key, value in record.items() if key != "sha256"}
    return oracle_sha256(canonical_bytes(body))


def build_reduced_pilot_record(
    *,
    baseline_sha: str,
    inventory: Mapping[str, Any],
    facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the pilot record. The historical ledger baseline is not rewritten."""

    _require_commit_sha(baseline_sha)
    observed = verified_scheduled_nightly_facts() if facts is None else dict(facts)
    cited = observed["cited_failure_runs"]
    if not isinstance(cited, list):
        raise ArchiveError("pilot facts are missing cited failure runs")
    observations: list[dict[str, Any]] = [dict(item) for item in cited]
    cancelled = observed.get("cited_cancelled_run")
    if isinstance(cancelled, Mapping):
        observations.append(dict(cancelled))
    assessment = assess_reduced_pilot_window(
        observations,
        configuration_id=PILOT_CONFIGURATION_ID,
        scheduled_success_total_count=observed["successful_total_count"],
        failure_total_count=observed["failure_total_count"],
        cancelled_total_count=observed["cancelled_total_count"],
        missing_total_count=observed["missing_total_count"],
        unknown_total_count=observed["unknown_total_count"],
        successful_evidence_days=PILOT_SUCCESS_RETENTION_FLOOR_DAYS,
        diagnostic_retention_days=PILOT_DIAGNOSTIC_RETENTION_FLOOR_DAYS,
        verified_archive_days=PILOT_VERIFIED_ARCHIVE_FLOOR_DAYS,
        actions_retention_cap_days=ACTIONS_RETENTION_CAP_DAYS,
        cadence_changed=False,
        retention_reduced=False,
        shallow_checkout=False,
        independent_review=False,
        independent_restore=False,
    )
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "reduced_pilot_48min",
        "issue": PILOT_ISSUE,
        "parent_issue": PARENT_ACCEPTANCE_ISSUE,
        "replaces_parent_acceptance": False,
        "decision_date": PILOT_DECISION_DATE,
        "decision_owner": "CI",
        "duration_minutes": PILOT_DURATION_MINUTES,
        "duration_unit": "wall_clock_minutes",
        "configuration_id": PILOT_CONFIGURATION_ID,
        "baseline_sha": baseline_sha,
        "baseline_ref": "origin/main",
        "status": assessment["status"],
        "equivalence": assessment["equivalence"],
        "reason_codes": assessment["reason_codes"],
        "sample": {
            "definition": (
                "Reduced pilot. One wall-clock window of 48 minutes, not 48 "
                "hours and not two runs. It starts only at the first successful "
                "scheduled Nightly (event=schedule, conclusion=success) on "
                f"configuration {PILOT_CONFIGURATION_ID} at or after "
                f"{PILOT_DECISION_UTC}. No backdating. A comparable pair is two "
                "different run ids on that same tested SHA and same "
                "configuration inside the window, one baseline arm and one "
                "candidate arm. A run is not its own oracle. Sample size is "
                "the number of such suitable pairs."
            ),
            "duration_minutes": PILOT_DURATION_MINUTES,
            "sample_size_pairs": assessment["sample_size_pairs"],
            "successful_scheduled_nightly_total_count": observed[
                "successful_total_count"
            ],
            "limits": [
                "Synthetic events fail closed.",
                "workflow_dispatch does not start the window.",
                "missing, unknown, cancelled, and failure are not success and are not zero.",
                "Mandatory skipped is not success. Expected skip of a non-mandatory weekly job can be success. Unknown duty plus skip stays unknown.",
                "Cancellation upload stays best-effort.",
                "Archive errors block the next stage.",
                f"This pilot does not replace acceptance of #{PARENT_ACCEPTANCE_ISSUE}.",
                "Cadence, retention, and shallow checkout stay unchanged.",
                "N2 stays blocked. independent_review and independent_restore stay false.",
            ],
        },
        "limitations": _pilot_limitations(observed),
        "retention_floors": {
            "successful_evidence_days": PILOT_SUCCESS_RETENTION_FLOOR_DAYS,
            "failed_or_cancelled_diagnostics_days": (
                PILOT_DIAGNOSTIC_RETENTION_FLOOR_DAYS
            ),
            "verified_archive_days": PILOT_VERIFIED_ARCHIVE_FLOOR_DAYS,
            "actions_cap_days": ACTIONS_RETENTION_CAP_DAYS,
        },
        "retention_changed": False,
        "cadence_changed": False,
        "shallow_checkout": False,
        "workflow_success_artifact_retention_days_unchanged": inventory.get(
            "workflow_success_artifact_retention_days"
        ),
        "workflow_success_artifacts_meet_floor": False,
        "actions_permissions_http": observed["actions_permissions_http"],
        "actions_permissions_source": observed["actions_permissions_source"],
        "n2_blocked": True,
        "independent_review": False,
        "independent_restore": False,
        "synthetic_events": False,
        "committed_gap_ledger_is_the_shadow_window": False,
        "cancellation_upload": "best_effort",
        "archive": {
            "status": "unavailable",
            "verified": False,
            "blocks_next_stage": True,
            "path": None,
        },
        "cited_failure_runs": cited,
        "cited_cancelled_run": observed["cited_cancelled_run"],
        "api_counts": assessment["counts"]["api"],
        "inventory": dict(inventory),
        "assessment": assessment,
    }
    record["sha256"] = pilot_record_sha256(record)
    return record


def require_pilot_advance(
    assessment: Mapping[str, Any],
    archive_root: Path,
) -> None:
    """Block the next stage. Archive errors come from verify_archive."""

    verify_archive(archive_root)
    if assessment.get("n2_blocked") is not False:
        raise ArchiveError("N2 stays blocked")
    if assessment.get("independent_review") is not True:
        raise ArchiveError("independent review is not granted")
    if assessment.get("independent_restore") is not True:
        raise ArchiveError("independent restore is not granted")
    if (
        assessment.get("equivalence") != "passed"
        or assessment.get("status") != "complete"
    ):
        raise ArchiveError("pilot window is not accepted")


def _write_canonical_record(destination: Path, record: Mapping[str, Any]) -> None:
    encoded = canonical_bytes(record)
    if destination.exists() and destination.read_bytes() != encoded:
        raise ArchiveError(f"refusing to overwrite {destination}")
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_create(destination, encoded, root=REPO_ROOT)


def _emit_github_output(name: str, value: str) -> None:
    handle_path = os.environ.get("GITHUB_OUTPUT")
    if not handle_path:
        return
    with Path(handle_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _command_partition(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--daily-outcome", default="")
    parser.add_argument("--validators-outcome", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    kind = partition_producer(args.daily_outcome, args.validators_outcome)
    bucket = partition_bucket(kind)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_class": kind,
        "upload_bucket": bucket,
        "success_retention_days": SUCCESS_RETENTION_DAYS,
        "diagnostic_retention_target_days": DIAGNOSTIC_RETENTION_DAYS,
        "actions_retention_cap_days": ACTIONS_RETENTION_CAP_DAYS,
        "cancellation_upload": "best_effort",
    }
    destination = resolve_cli_path(args.output, root=REPO_ROOT)
    if destination.name != PARTITION_NAME:
        raise ArchiveError(f"partition report must be named {PARTITION_NAME}")
    encoded = canonical_bytes(payload)
    if destination.exists() and destination.read_bytes() != encoded:
        raise ArchiveError(f"refusing to overwrite {destination}")
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        _atomic_create(destination, encoded, root=REPO_ROOT)
    _emit_github_output("class", kind)
    _emit_github_output("bucket", bucket)
    print(bucket)
    return 0


def _command_aggregate(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--event", required=True)
    parser.add_argument("--dow", default="")
    parser.add_argument("--dom", default="")
    parser.add_argument("--month", default="")
    parser.add_argument("--force-weekly", default="")
    parser.add_argument("--result", action="append", default=[])
    args = parser.parse_args(argv)
    results: dict[str, str] = {}
    for token in args.result:
        name, separator, value = str(token).partition("=")
        if not separator or name not in JOB_KINDS:
            raise ArchiveError(f"unknown job result: {token}")
        results[name] = value
    report = aggregate_results(
        results,
        dow=args.dow,
        dom=args.dom,
        month=args.month,
        force_weekly=args.force_weekly,
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "success" else 1


def _command_verify(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--archive", required=True)
    args = parser.parse_args(argv)
    root = resolve_cli_path(args.archive, root=REPO_ROOT)
    report = verify_archive(root)
    print(json.dumps(report, sort_keys=True))
    return 0


def _command_require_accepted(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--ledger", required=True)
    args = parser.parse_args(argv)
    path = resolve_cli_path(args.ledger, root=REPO_ROOT)
    if not path.is_file():
        raise ArchiveError(f"archive unavailable: {path}")
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArchiveError(f"malformed ledger: {path}") from exc
    if not isinstance(ledger, dict):
        raise ArchiveError(f"malformed ledger: {path}")
    require_accepted(ledger)
    return 0


def _workflow_endpoint(
    repository: str,
    workflow: str,
    *,
    branch: str | None,
    event: str | None,
    page: int,
    page_size: int,
) -> str:
    params: dict[str, str | int] = {"per_page": page_size, "page": page}
    if branch:
        params["branch"] = branch
    if event:
        params["event"] = event
    workflow_id = quote(workflow, safe="")
    return (
        f"repos/{repository}/actions/workflows/{workflow_id}/runs?{urlencode(params)}"
    )


def _command_archive(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", default="nightly.yml")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--event", default="schedule")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = resolve_cli_path(args.output, root=REPO_ROOT)
    output.mkdir(parents=True, exist_ok=True)
    client = ReadOnlyGitHubClient(REPO_ROOT)
    report = archive_runs(
        client,
        args.repository,
        workflow=args.workflow,
        branch=args.branch or None,
        event=args.event or None,
        limit=args.limit,
        output=output,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


def _window_protocol() -> dict[str, Any]:
    """Rules for a future window. They do not rewrite the historical gap ledger."""

    return {
        "minimum_span": (
            "48 wall-clock hours after the start observation (two full days), "
            "not two calendar-date hops and not two runs"
        ),
        "start_rule": (
            "Set window_start_sha and window_start_utc only after this daily "
            "configuration is merged and the first valid comparable "
            "baseline/candidate observation exists. Record both SHAs, both "
            "UTCs, and the configuration id. Do not backdate."
        ),
        "completeness": [
            "Each UTC day in the half-open span has the schedule attempts for that fixed configuration.",
            "Each attempt keeps raw.json, outcomes.json, and manifest.json.",
            "verify-archive matches every index run/attempt pair and its raw SHA-256.",
            "Pagination status is complete. Unknown and incomplete stay unknown, not success.",
            "The oracle compares baseline and candidate outcomes on the same inputs and does not call the schedule classifier.",
        ],
        "gaps": [
            "A missing day, artifact, or API page stays missing. It is not success and not zero.",
            "Cancellation upload is best-effort. The existing read-only timing collector backfills from the Actions API when that upload is absent.",
            "If the collector cannot read the attempt, record the gap. Do not rebuild it from another SHA or date.",
            "Historical failures and gap reasons remain in the unacceptable ledger. Do not delete or rewrite those snapshots.",
        ],
        "invalid_when": [
            "The span is shorter than 48 wall-clock hours.",
            "A UTC day inside the observed span is missing a schedule attempt.",
            "Baseline and candidate configurations are mixed in one comparable group.",
            "The candidate arm is absent.",
            "Checksum, run id, attempt, or head SHA does not match the indexed raw JSON.",
            "An indexed snapshot directory or manifest is missing.",
            "Cadence or retention of the fixed configuration changes during the window.",
        ],
    }


def _command_record_pilot(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    destination = resolve_cli_path(args.output, root=REPO_ROOT)
    if destination.name != PILOT_RECORD_NAME:
        raise ArchiveError(f"pilot record must be named {PILOT_RECORD_NAME}")
    record = build_reduced_pilot_record(
        baseline_sha=args.baseline_sha,
        inventory=nightly_check_inventory(REPO_ROOT),
    )
    _write_canonical_record(destination, record)
    print(record["status"])
    return 0


def _command_record_window(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--index", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--candidate-pairs", type=int, default=0)
    parser.add_argument("--artifact-retention-days", type=int, required=True)
    parser.add_argument("--actions-retention-cap-days", type=int, required=True)
    parser.add_argument("--actions-permissions-http", required=True)
    parser.add_argument("--actions-execution-observed", required=True)
    parser.add_argument("--cadence-changed-before-acceptance", action="store_true")
    args = parser.parse_args(argv)
    index_path = resolve_cli_path(args.index, root=REPO_ROOT)
    if index_path.name != ARCHIVE_INDEX_NAME:
        raise ArchiveError(f"archive index must be named index.json: {index_path}")
    runs = verify_archive(index_path.parent)["snapshots"]
    historical = assess_shadow_window(
        runs,
        candidate_pairs=args.candidate_pairs,
        artifact_retention_days=args.artifact_retention_days,
        actions_retention_cap_days=args.actions_retention_cap_days,
        independent_review=False,
        cadence_changed_before_acceptance=args.cadence_changed_before_acceptance,
    )
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "baseline_sha": args.baseline_sha,
        "recorded_at": args.recorded_at,
        "decision_owner": "CI",
        "reviewer_roles": [
            "security",
            "test-subject-owner",
            "evidence-keeper",
        ],
        "personal_assignees": [],
        "independent_review_record": None,
        "window_start_sha": None,
        "window_start_utc": None,
        "restored_daily_jobs": [
            "tests",
            "e2e",
            "duplication",
            "import-linter",
            "generated-artifact-daily",
        ],
        "frequency_change_pr": 12452,
        "actions_permissions_http": args.actions_permissions_http,
        "actions_execution_observed": args.actions_execution_observed == "true",
        "historical_window": historical,
        "durable_archive": {
            "actions_success_retention_days": SUCCESS_RETENTION_DAYS,
            "actions_failure_retention_days": DIAGNOSTIC_RETENTION_DAYS,
            "actions_cancellation_retention_days": DIAGNOSTIC_RETENTION_DAYS,
            "actions_service_cap_days": ACTIONS_RETENTION_CAP_DAYS,
            "git_path": "reports/governance/n1-shadow-window",
            "policy": (
                "Append-only git snapshots under reports/governance/n1-shadow-window. "
                "An existing run/attempt is not overwritten. Presence in git is the "
                "storage location, not proof that the bytes survive or were restored."
            ),
            "minimum_days": 90,
            "elapsed_age_is_90_days": False,
            "independent_restore": False,
            "acceptance": "not_pass",
            "local_verify_archive_is_author_check_only": True,
        },
        "window_protocol": _window_protocol(),
        "next_window": {
            "status": "not_started",
            "minimum_hours": 48,
            "configuration_id": "daily-deterministic-plus-existing-weekly-security",
            "continuation": (
                "Start the 48-hour (two full day) window only after this "
                "daily configuration is on main and the first valid "
                "comparable observation exists. Record that observation "
                "SHA and UTC then. Do not backdate it and do not mix it "
                "with the unacceptable history below. Durable archive "
                "acceptance still requires the 90-day age gate before N1 "
                "can close. Do not continue N2 before that."
            ),
        },
    }
    destination = resolve_cli_path(args.output, root=REPO_ROOT)
    encoded = canonical_bytes(ledger)
    if destination.exists() and destination.read_bytes() != encoded:
        raise ArchiveError(f"refusing to overwrite {destination}")
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        _atomic_create(destination, encoded, root=REPO_ROOT)
    print(historical["status"])
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one shadow-evidence command."""

    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw or raw[0] not in {
        "partition",
        "aggregate",
        "verify-archive",
        "require-accepted",
        "archive",
        "record-window",
        "record-pilot",
    }:
        print(
            "usage: nightly-shadow {partition|aggregate|verify-archive|"
            "require-accepted|archive|record-window|record-pilot}",
            file=sys.stderr,
        )
        return 2
    command, rest = raw[0], raw[1:]
    try:
        if command == "partition":
            return _command_partition(rest)
        if command == "aggregate":
            return _command_aggregate(rest)
        if command == "verify-archive":
            return _command_verify(rest)
        if command == "require-accepted":
            return _command_require_accepted(rest)
        if command == "archive":
            return _command_archive(rest)
        if command == "record-pilot":
            return _command_record_pilot(rest)
        return _command_record_window(rest)
    except (ArchiveError, GitHubReviewError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
