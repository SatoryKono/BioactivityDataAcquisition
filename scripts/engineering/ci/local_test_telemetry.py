"""Validate complete local coverage evidence without assigning a CI identity."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


def junit_telemetry_sha256(path: Path) -> str:
    """Bind case identity, duration and outcome, independent of redacted logs."""
    root = ElementTree.parse(path).getroot()
    rows = [
        {
            "attributes": dict(sorted(case.attrib.items())),
            "outcomes": [
                child.tag
                for child in case
                if child.tag
                in {
                    "failure",
                    "error",
                    "skipped",
                }
            ],
        }
        for case in root.iter("testcase")
    ]
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def validate_local_measurement(
    manifest_path: Path,
    *,
    repo_root: Path,
    test_tree_sha256: str,
    source_tree_sha256: str,
) -> dict[str, Any]:
    """Reject incomplete, stale, failed or substituted inputs before publication.

    Dynamic JSON/XML values stay at this external evidence boundary. The
    resulting receipt is local_single_host evidence, never a CI attestation.
    """
    from scripts.engineering.qa.run_local_coverage_verify import SHARDS

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        started = datetime.fromisoformat(payload["started_at_utc"])
        finished = datetime.fromisoformat(payload["finished_at_utc"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "Local measurement requires valid start/completion timestamps"
        ) from error
    if (
        started.tzinfo is None
        or finished.tzinfo is None
        or not (started <= finished <= datetime.now(UTC))
    ):
        raise ValueError(
            "Local measurement timestamps must be ordered and not in the future"
        )
    branch = str(payload.get("source_branch", ""))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch) or ".." in branch:
        raise ValueError("Local measurement requires a valid source branch")
    names = [shard.name for shard in SHARDS]
    if (
        payload.get("producer") != "run_local_coverage_verify.py"
        or payload.get("complete") is not True
        or payload.get("required_shards") != names
        or [row.get("name") for row in payload.get("shards", [])] != names
        or payload.get("line_gate_exit_code") != 0
        or payload.get("branch_gate_exit_code") != 0
    ):
        raise ValueError("Telemetry requires all 17 successful canonical shards")
    if payload.get("test_tree_sha256") != test_tree_sha256 or (
        payload.get("source_tree_sha256") != source_tree_sha256
    ):
        raise ValueError("Local telemetry measurement source/test tree drifted")
    commit = str(payload.get("head", ""))
    if (
        len(commit) != 40
        or subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("Local measurement commit must be an ancestor of HEAD")
    xml = Path(payload["coverage_xml"])
    if hashlib.sha256(xml.read_bytes()).hexdigest() != payload["coverage_xml_sha256"]:
        raise ValueError("Local coverage XML digest mismatch")
    coverage = ElementTree.parse(xml).getroot()
    for field, attribute in (
        ("line_percent", "line-rate"),
        ("branch_percent", "branch-rate"),
    ):
        percent = round(float(coverage.attrib[attribute]) * 100, 2)
        if percent < 85 or percent != payload[field]:
            raise ValueError("Local coverage thresholds or manifest values mismatch")
    junit_paths = []
    durations = {}
    counts = {"passed": 0, "skipped": 0}
    for row in payload["shards"]:
        path = Path(row["junit_file"])
        if row["exit_code"] != 0 or not re.fullmatch(
            r"[0-9a-f]{64}", str(row.get("coverage_sha256", ""))
        ):
            raise ValueError("Local shard failed or has no coverage evidence")
        if junit_telemetry_sha256(path) != row.get("junit_telemetry_sha256"):
            raise ValueError("Local JUnit telemetry digest mismatch")
        cases = list(ElementTree.parse(path).getroot().iter("testcase"))
        if not cases or any(
            case.find("failure") is not None or case.find("error") is not None
            for case in cases
        ):
            raise ValueError("Local JUnit has failures, errors or no test cases")
        skipped = sum(case.find("skipped") is not None for case in cases)
        counts["skipped"] += skipped
        counts["passed"] += len(cases) - skipped
        durations[path.name] = round(
            sum(float(case.get("time", "0")) for case in cases), 3
        )
        junit_paths.append(path)
    return {
        "manifest": payload,
        "junit_paths": junit_paths,
        "coverage_xml": xml,
        "counts": counts,
        "duration_sums": durations,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }


def build_local_baseline(manifest_path: Path, *, repo_root: Path) -> dict[str, Any]:
    """Materialize telemetry exclusively from the verified local artifacts."""
    from scripts.engineering.ci.update_test_telemetry_baseline import (
        build_baseline_payload,
        compute_test_telemetry_source_tree_sha256,
    )
    from scripts.engineering.qa.report_module_coverage_inventory import (
        compute_source_tree_sha256,
    )

    capture = validate_local_measurement(
        manifest_path,
        repo_root=repo_root,
        test_tree_sha256=compute_test_telemetry_source_tree_sha256(repo_root),
        source_tree_sha256=compute_source_tree_sha256(repo_root=repo_root),
    )
    manifest = capture["manifest"]
    payload = build_baseline_payload(
        coverage_xml_path=capture["coverage_xml"],
        coverage_percent=None,
        coverage_log_path=None,
        slowest_json_path=manifest_path.parent / "not-a-cached-ci-summary.json",
        junit_paths=capture["junit_paths"],
        source_branch=manifest["source_branch"],
        source_commit=manifest["head"],
        source_run_id="local-" + manifest_path.parent.name,
        source_event="local_coverage_verify",
        source_run_url="",
        coverage_threshold=85.0,
        source_tree_sha256=manifest["test_tree_sha256"],
        prefer_junit=True,
    )
    payload["refreshed_at_utc"] = manifest["finished_at_utc"]
    payload["duration_telemetry"]["total_cases"] = capture["counts"]["passed"]
    payload["duration_telemetry"]["execution_context"].update(
        {
            "executed_count": capture["counts"]["passed"],
            "skipped_count": capture["counts"]["skipped"],
            "worker_mode": "canonical local 17-shard plan; per-shard command recorded",
            "junit_testcase_duration_sum_s": capture["duration_sums"],
            "lane_wall_time_s": {
                row["name"]: row["seconds"] for row in manifest["shards"]
            },
            "lane_wall_time_source": "producer_monotonic_clock",
            "explicit_exclusions": [
                {
                    "lane": "live-provider-contracts",
                    "reason": "canonical contract-confidence marker excludes live network-owned contracts",
                },
                {
                    "lane": "performance",
                    "reason": "benchmark-owned non-blocking workflow; outside the canonical 17-group plan",
                },
                {
                    "lane": "manual-e2e",
                    "reason": "operator-triggered external-runtime lane; excluded by the canonical serial command",
                },
                {
                    "lane": "architecture",
                    "reason": "architecture gates run separately, outside product coverage",
                },
                {
                    "lane": "memory",
                    "reason": "existing canonical 17-group marker selection excludes memory; commands remain unchanged",
                },
            ],
        }
    )
    payload["measurement_provenance"] = {
        "producer": manifest["producer"],
        "trust_tier": "local_single_host",
        "ci_status": "BLOCKED_EXTERNAL_PERMANENT",
        "complete": True,
        "manifest_sha256": capture["manifest_sha256"],
        "coverage_xml_sha256": manifest["coverage_xml_sha256"],
        "source_tree_sha256": manifest["source_tree_sha256"],
        "test_tree_sha256": manifest["test_tree_sha256"],
        "head": manifest["head"],
        "required_shards": manifest["required_shards"],
        "started_at_utc": manifest["started_at_utc"],
        "finished_at_utc": manifest["finished_at_utc"],
        "shards": [
            {
                key: row[key]
                for key in (
                    "name",
                    "exit_code",
                    "seconds",
                    "coverage_sha256",
                    "junit_telemetry_sha256",
                )
            }
            for row in manifest["shards"]
        ],
    }
    return payload
