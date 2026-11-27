"""Workflow inventory and canonical pilot-record contracts for N1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.engineering.ci.nightly_shadow_archive as archive_module
from scripts.engineering.ci.nightly_shadow_archive import (
    ArchiveError,
    JOB_KINDS,
    PILOT_CONFIGURATION_ID,
    PILOT_RECORD_NAME,
    REPO_ROOT,
    build_reduced_pilot_record,
    canonical_bytes,
    main,
    nightly_check_inventory,
    pilot_record_sha256,
)

pytestmark = pytest.mark.unit
BASELINE_SHA = "c41cd6f7b7e4f1cb841358837fec6c6d30625106"


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
        "codeql-freshness",
        "github-settings",
        "scorecard",
        "security",
        "zizmor",
    }
    by_name = {row["name"]: row for row in inventory["jobs"]}
    assert by_name["security"]["schedule_kind"] == "security_daily"
    assert by_name["security"]["observation_class"] == "external_state_security"
    assert by_name["codeql"]["cadence"] == "weekly_monday"
    assert by_name["codeql-freshness"]["cadence"] == "every_scheduled_nightly"
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
