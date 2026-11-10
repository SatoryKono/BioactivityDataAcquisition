"""Build the separate, fail-closed 207-resource runtime observation register.

The source inventory is read-only. An observed allocation is partial evidence;
neither a green suite nor a matching test name certifies all scenario barriers.
"""

from __future__ import annotations

import hashlib
import gzip
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from scripts.engineering.qa.runtime_acceptance_12553 import (
    BUNDLE,
    ROOT,
    evidence_exists,
    evidence_names,
    read_evidence,
)

RUNS = (
    "files-config-final",
    "tasks-executors",
    "storage-export-final",
    "http-telemetry",
    "health-composition",
)
LIMITS = {
    "delta": "Native delta-rs object/worker completion and commit boundaries were not instrumented; historical #12106 crash evidence is not a current-head shutdown receipt.",
    "file-lock": "No cross-process acquisition/release observation at this lock site; Windows has no fcntl and POSIX lock tests skip. Windows/native locking needs its own measured branch.",
    "process": "No owned child PID, exit/wait and pipe-drain receipt at this production spawn site. Generic process exit or mocked subprocess tests cannot certify it.",
    "http": "The HTTP suites ran, but no real transport/pool-close observation was attached to this client's creation site. Mocked request success is insufficient.",
    "library-http": "No local library transport fixture with request/response/pool identities and shutdown correlation; production endpoints are prohibited.",
    "http-response": "No correlated real response/socket closure at this request site; mocked HTTP tests do not prove physical transport shutdown.",
    "streamed-http-response": "No real streamed-response read/error/cancel barriers with response closure and retained connection accounting.",
    "temp": "File observations do not account for temporary-path deletion/rename and OS handles at every allocation/cleanup boundary.",
    "loop-worker": "Cancelling an await does not prove default-executor thread completion; no loop-wide worker join/remaining-thread receipt was captured.",
    "server": "Health suites ran, but accepted socket IDs, server wait_closed and remaining connection/task sets were not correlated.",
    "connection": "No accepted-connection transport/writer close and wait_closed receipt; handler tests alone do not certify socket shutdown.",
    "tracing": "Tracing tests use SDK/exporter doubles; no actual provider/processor/exporter shutdown and retained-worker receipt.",
    "metrics": "No actual metrics server socket/thread stop receipt; no monitoring stack was started.",
    "logging": "Logging configuration tests ran, but no complete FileHandler creation/flush/close set was correlated with this allocation site.",
    "compression": "No compressor stream finalization and underlying file closure receipt at this creation site.",
    "arrow": "No native Arrow reader/buffer mapping ownership and release receipt at this allocation site.",
    "thread": "No physical worker join receipt at this site; future cancellation is not worker shutdown.",
    "pipe-reader-thread": "No two-reader-thread join, child PID and pipe-end closure set at the bounded-subprocess boundary.",
    "table-file": "Export tests ran, but native table reader/writer handles and completion were not observed at this allocation site.",
    "xlsx-save-resource-set": "XLSX save includes archive/file resources not covered by plain io.open observations; complete native/archive shutdown is unmeasured.",
    "xlsx-writer": "No ExcelWriter/archive close receipt with all underlying handles after success/error.",
    "file-copy": "No complete source/destination copy handle set and interrupted-copy cleanup receipt at this site.",
    "directory": "Directory creation/removal lifetime is not an iterator-close receipt; retained output ownership is unmeasured.",
}


LOCK_TESTS = {
    "test_reentrant_lock_normal_acquisition_and_release",
    "test_reentrant_lock_error_release",
    "test_missing_release_detectable",
    "test_directory_walk_normal",
    "test_directory_glob_normal",
}


def _event_path(run: str) -> Path:
    candidates = (
        f"qualified-{run}-events.json.gz",
        f"{run}-events.json.gz",
        f"{run}-events.json",
    )
    return next(
        (BUNDLE / name for name in candidates if evidence_exists(name, BUNDLE)),
        BUNDLE / candidates[0],
    )


def _observer_provenance(path: Path) -> dict:
    receipt_path = BUNDLE / (path.name.split("-events.json")[0] + "-command.json")
    receipt = json.loads(read_evidence(receipt_path.name, BUNDLE))
    observer = "tests/helpers/runtime_acceptance_12553.py"
    expected = hashlib.sha256((ROOT / observer).read_bytes()).hexdigest()
    if receipt.get("input_sha256", {}).get(observer) != expected:
        raise ValueError(f"unqualified observer version: {receipt_path.name}")
    for field in ("head_sha", "tree_sha"):
        if re.fullmatch(r"[0-9a-f]{40}", str(receipt.get(field))) is None:
            raise ValueError(f"missing Git identity: {receipt_path.name}")
    return {
        "command": receipt_path.name,
        "head_sha": receipt["head_sha"],
        "tree_sha": receipt["tree_sha"],
        "observer_sha256": expected,
        "trace": path.name,
        "trace_sha256": hashlib.sha256(read_evidence(path.name, BUNDLE)).hexdigest(),
    }


def _observations(identities: set[str]) -> tuple[dict, list[dict]]:
    evidence: dict[str, list[dict]] = defaultdict(list)
    provenance = []
    for run in RUNS:
        path = _event_path(run)
        raw = read_evidence(path.name, BUNDLE)
        payload = json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)
        for index, event in enumerate(payload["events"]):
            for identity in event["identities"]:
                if identity not in identities:
                    raise ValueError(f"unknown observed resource: {identity}")
                evidence[identity].append(
                    {**event, "trace": f"{path.name}#/events/{index}"}
                )
        provenance.append(_observer_provenance(path))
    return evidence, provenance


def _successful_control(prefix: str) -> bool:
    receipt = json.loads(read_evidence(f"{prefix}-command.json", BUNDLE))
    exit_code = int(read_evidence(f"{prefix}-exit-code.txt", BUNDLE))
    if (
        receipt.get("exit_code") != 0
        or exit_code != 0
        or receipt.get("timed_out") is not False
    ):
        return False
    if not read_evidence(f"{prefix}-stdout.txt", BUNDLE):
        return False
    root = ET.fromstring(read_evidence(f"{prefix}-junit.xml", BUNDLE))
    suites = list(root.iter("testsuite"))
    if not suites or any(
        int(s.get(k, "0")) for s in suites for k in ("failures", "errors", "skipped")
    ):
        return False
    cases = list(root.iter("testcase"))
    return (
        len(cases) == len(LOCK_TESTS)
        and {case.get("name") for case in cases} == LOCK_TESTS
        and all(len(case) == 0 for case in cases)
        and sum(int(s.get("tests", "0")) for s in suites) == len(LOCK_TESTS)
    )


def lock_control() -> tuple[bool, list[str]]:
    """An absent, failed, skipped or malformed control cannot assert a boundary."""
    qualified = any(
        name.startswith("qualified-review-controls-") for name in evidence_names(BUNDLE)
    )
    prefix = "qualified-review-controls" if qualified else "review-controls"
    refs = [f"{prefix}-stdout.txt", f"{prefix}-junit.xml"]
    try:
        passed = _successful_control(prefix)
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
        passed = False
    return passed, [name for name in refs if evidence_exists(name, BUNDLE)]


def _remaining(event: dict) -> bool:
    return (
        event.get("closed_after_teardown") is False
        or event.get("done_after_teardown") is False
        or event.get("remaining_threads", 0) > 0
        or (
            event.get("event") == "executor-created"
            and not event.get("shutdown_after_teardown")
        )
    )


def _reason(
    resource: dict, observed: list[dict], missing: list[str], lock_passed: bool
) -> str:
    if resource["identity"] == "diagnostics.metric_inventory.reentrant-lock":
        if lock_passed:
            return "Normal/error lock assertions and monkeypatch negative control pass; inner collector is substituted. Owner cancellation/deadline/retry boundaries are not measured."
        return "Lock review control is missing, failed, skipped or malformed; normal/error boundaries and negative control are NOT_VERIFIABLE."
    if observed:
        return (
            "Allocation/teardown observations exist, but not all before/use/close error, owner cancellation, deadline and retry barriers are measured. "
            f"Unobserved creation sites: {len(missing)}."
        )
    return LIMITS.get(
        resource["type"],
        "No real allocation/close event at this exact site in the selected owning suites. A mocked or unexercised creator path cannot certify resource shutdown.",
    )


def _event_indexes(observed: list[dict]) -> dict[str, list[int]]:
    indexes: dict[str, list[int]] = defaultdict(list)
    for event in observed:
        name, _, pointer = event["trace"].partition("#")
        indexes[name].append(int(pointer.rsplit("/", 1)[-1]))
    return dict(indexes)


def _scenario_rows(resource: dict, reason: str, lock_passed: bool) -> dict:
    scenarios = {
        name: {
            **scenario,
            "register_result": "NOT_VERIFIABLE",
            "reason": reason + " Required barrier: " + scenario["observation"],
        }
        for name, scenario in resource["scenarios"].items()
    }
    if lock_passed:
        for name in ("normal", "error"):
            scenarios[name]["register_result"] = "ASSERTED_LOCK_BOUNDARY"
    return scenarios


def _resource_row(
    resource: dict, observed: list[dict], control: tuple[bool, list[str]]
) -> dict:
    expected_sites = {f"{s['file']}:{s['line']}" for s in resource["creation_sites"]}
    observed_sites = {s for e in observed for s in e["sites"]}
    missing = sorted(expected_sites - observed_sites)
    is_lock = resource["identity"] == "diagnostics.metric_inventory.reentrant-lock"
    lock_passed = is_lock and control[0]
    reason = _reason(resource, observed, missing, lock_passed)
    indexes = _event_indexes(observed)
    return {
        "identity": resource["identity"],
        "family": resource["type"],
        "status": "EXECUTED_PARTIAL" if observed or lock_passed else "NOT_VERIFIABLE",
        "reason": reason,
        "creator": resource["creator"],
        "owner": resource["owner"],
        "closer": resource["closer"],
        "shutdown_contract": resource["shutdown_contract"],
        "creation_sites": sorted(expected_sites),
        "unobserved_sites": missing,
        "observed_event_count": len(observed),
        "observed_sites": sorted(observed_sites),
        "trace_refs": control[1] if is_lock else sorted(indexes),
        "event_indexes": indexes,
        "remaining_observations": [e["trace"] for e in observed if _remaining(e)],
        "scenarios": _scenario_rows(resource, reason, lock_passed),
    }


def build() -> dict:
    """Require every inventory identity and preserve exact scenario expectations."""
    catalog = ROOT / "configs/quality/external_resource_inventory.json"
    inventory = json.loads(catalog.read_text(encoding="utf-8"))
    resources = [
        r
        for part in inventory["resource_parts"]
        for r in json.loads((ROOT / part["file"]).read_text(encoding="utf-8"))[
            "resources"
        ]
    ]
    identities = {r["identity"] for r in resources}
    if len(resources) != 207 or len(identities) != 207:
        raise ValueError("expected exactly 207 unique inventory resources")
    evidence, provenance = _observations(identities)
    control = lock_control()
    rows = [_resource_row(r, evidence[r["identity"]], control) for r in resources]
    inputs = [catalog, *(ROOT / part["file"] for part in inventory["resource_parts"])]
    return {
        "issue": 12553,
        "resource_count": len(rows),
        "full_runtime_acceptance": False,
        "semantics": "EXECUTED_PARTIAL is an allocation/teardown observation, not acceptance of every creation site or scenario. NOT_VERIFIABLE is explicit residual work, not an accepted waiver.",
        "inventory_sha256": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in inputs
        },
        "observation_provenance": provenance,
        "families": dict(sorted(Counter(r["family"] for r in rows).items())),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "resources": rows,
    }


def main() -> None:
    payload = build()
    (BUNDLE / "coverage-register.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# 207-resource runtime coverage register",
        "",
        payload["semantics"],
        "",
        "| Identity | Family | Result | Evidence | Residual reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["resources"]:
        refs = ", ".join(row["trace_refs"]) or "none"
        lines.append(
            f"| {row['identity']} | {row['family']} | {row['status']} | {refs} | {row['reason']} |"
        )
    (BUNDLE / "coverage-register.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["status_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
