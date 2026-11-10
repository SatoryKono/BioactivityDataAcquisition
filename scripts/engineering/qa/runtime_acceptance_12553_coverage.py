"""Build the separate, fail-closed 207-resource runtime observation register.

The source inventory is read-only. An observed allocation is partial evidence;
neither a green suite nor a matching test name certifies all scenario barriers.
"""

from __future__ import annotations

import hashlib
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.engineering.qa.runtime_acceptance_12553 import BUNDLE, ROOT

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
    evidence: dict[str, list[dict]] = defaultdict(list)
    for run in RUNS:
        path = BUNDLE / f"{run}-events.json"
        qualified = BUNDLE / f"qualified-{run}-events.json.gz"
        if qualified.exists():
            path = qualified
        elif path.with_suffix(".json.gz").exists():
            path = path.with_suffix(".json.gz")
        raw = (
            gzip.decompress(path.read_bytes())
            if path.suffix == ".gz"
            else path.read_bytes()
        )
        payload = json.loads(raw)
        for index, event in enumerate(payload["events"]):
            for identity in event["identities"]:
                if identity not in identities:
                    raise ValueError(f"unknown observed resource: {identity}")
                evidence[identity].append(
                    {"trace": f"{path.name}#/events/{index}", **event}
                )
    rows = []
    for resource in resources:
        identity = resource["identity"]
        observed = evidence[identity]
        expected_sites = {
            f"{s['file']}:{s['line']}" for s in resource["creation_sites"]
        }
        observed_sites = {s for e in observed for s in e["sites"]}
        missing = sorted(expected_sites - observed_sites)
        reason = LIMITS.get(
            resource["type"],
            "No real allocation/close event at this exact site in the selected owning suites. A mocked or unexercised creator path cannot certify resource shutdown.",
        )
        if observed:
            reason = (
                "Allocation/teardown observations exist, but not all before/use/close error, owner cancellation, deadline and retry barriers are measured. "
                f"Unobserved creation sites: {len(missing)}."
            )
        boundary = identity == "diagnostics.metric_inventory.reentrant-lock"
        if boundary:
            reason = "Normal/error lock assertions and monkeypatch negative control pass; inner collector is substituted. Owner cancellation/deadline/retry boundaries are not measured."
        remaining = [
            e["trace"]
            for e in observed
            if e.get("closed_after_teardown") is False
            or e.get("done_after_teardown") is False
            or e.get("remaining_threads", 0) > 0
            or (
                e.get("event") == "executor-created"
                and not e.get("shutdown_after_teardown")
            )
        ]
        row = {
            "identity": identity,
            "family": resource["type"],
            "status": "EXECUTED_PARTIAL" if observed or boundary else "NOT_VERIFIABLE",
            "reason": reason,
            "creator": resource["creator"],
            "owner": resource["owner"],
            "closer": resource["closer"],
            "shutdown_contract": resource["shutdown_contract"],
            "creation_sites": sorted(expected_sites),
            "unobserved_sites": missing,
            "observed_event_count": len(observed),
            "observed_sites": sorted(observed_sites),
            "trace_refs": sorted({e["trace"].split("#")[0] for e in observed}),
            "event_indexes": {
                filename: [
                    int(e["trace"].split("/")[-1])
                    for e in observed
                    if e["trace"].startswith(filename + "#")
                ]
                for filename in sorted({e["trace"].split("#")[0] for e in observed})
            },
            "remaining_observations": remaining,
            "scenarios": {
                name: {
                    **scenario,
                    "register_result": "NOT_VERIFIABLE",
                    "reason": reason + " Required barrier: " + scenario["observation"],
                }
                for name, scenario in resource["scenarios"].items()
            },
        }
        if boundary:
            row["trace_refs"] = [
                "review-controls-stdout.txt",
                "review-controls-junit.xml",
            ]
            for name in ("normal", "error"):
                row["scenarios"][name]["register_result"] = "ASSERTED_LOCK_BOUNDARY"
        rows.append(row)
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
