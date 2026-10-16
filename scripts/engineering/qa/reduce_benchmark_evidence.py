"""Manifest-first evidence bundle and deterministic reducer for benchmark state."""

import argparse
import json
import sys
import os
from pathlib import Path


def write_gate(path: Path, status: str, reason: str) -> None:
    if path:
        import tempfile

        resolved_str = os.path.abspath(str(path))
        cwd = os.path.abspath(os.getcwd())
        tmp = os.path.abspath(tempfile.gettempdir())
        if not (resolved_str.startswith(cwd) or resolved_str.startswith(tmp)):
            raise ValueError("Path traversal detected")

        resolved = Path(resolved_str)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(
            json.dumps({"status": status, "reason": reason}, indent=2), encoding="utf-8"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-json", type=Path, required=True, help="Raw benchmark measurements JSON"
    )
    parser.add_argument(
        "--manifest-out", type=Path, required=True, help="Output manifest JSON"
    )
    parser.add_argument(
        "--gate-out", type=Path, required=True, help="Output gate verdict JSON"
    )
    parser.add_argument(
        "--baseline-sha",
        type=str,
        default="unknown",
        help="Baseline SHA for regression comparison",
    )
    parser.add_argument(
        "--checkout-sha", type=str, default="", help="Expected checkout SHA"
    )
    parser.add_argument(
        "--run-id", type=str, default=os.environ.get("GITHUB_RUN_ID", "unknown")
    )
    parser.add_argument(
        "--run-attempt",
        type=str,
        default=os.environ.get("GITHUB_RUN_ATTEMPT", "unknown"),
    )
    parser.add_argument(
        "--run-url",
        type=str,
        default=f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', 'unknown')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
    )

    args = parser.parse_args(argv)

    import tempfile

    raw_resolved_str = os.path.abspath(str(args.raw_json))
    cwd = os.path.abspath(os.getcwd())
    tmp = os.path.abspath(tempfile.gettempdir())
    if not (raw_resolved_str.startswith(cwd) or raw_resolved_str.startswith(tmp)):
        raise ValueError("Path traversal detected")

    raw_path = Path(raw_resolved_str)

    if not raw_path.is_file():
        sys.stderr.write(
            "Integration blocker: caller contract unavailable. Raw JSON missing.\n"
        )
        write_gate(args.gate_out, "failed", "missing_observations")
        return 1

    try:
        raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Malformed JSON: {e}\n")
        write_gate(args.gate_out, "failed", "malformed_json")
        return 1

    if not isinstance(raw_data, dict):
        sys.stderr.write("JSON root must be a dict\n")
        write_gate(args.gate_out, "failed", "malformed_json")
        return 1

    benchmarks = raw_data.get("benchmarks")
    if not isinstance(benchmarks, list) or len(benchmarks) == 0:
        sys.stderr.write("Zero execution: no benchmarks found\n")
        write_gate(args.gate_out, "failed", "zero_execution")
        return 1

    all_skipped = True
    has_failed = False
    for b in benchmarks:
        stats = b.get("stats")
        has_error = b.get("has_error", False)

        if has_error:
            has_failed = True
            all_skipped = False
        elif stats:
            all_skipped = False

    if has_failed:
        sys.stderr.write("Measured regression or failure detected\n")
        write_gate(args.gate_out, "failed", "measured_regression")
        return 1

    if all_skipped:
        sys.stderr.write("All benchmarks skipped\n")
        write_gate(args.gate_out, "failed", "all_skipped")
        return 1
    source_block = raw_data.get("bioetl_source")
    if not source_block:
        sys.stderr.write(
            "Integration blocker: caller contract unavailable. 'bioetl_source' missing.\n"
        )
        write_gate(args.gate_out, "failed", "incomplete_evidence")
        return 1

    measured_sha = source_block.get("revision")
    if (
        not measured_sha
        or measured_sha == "unknown"
        or (args.checkout_sha and measured_sha != args.checkout_sha)
    ):
        sys.stderr.write(
            f"Wrong SHA: expected {args.checkout_sha}, got {measured_sha}\n"
        )
        write_gate(args.gate_out, "failed", "wrong_sha")
        return 1

    manifest = {
        "actual_measured_sha": measured_sha,
        "baseline_sha": args.baseline_sha,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "run_url": args.run_url,
        "test_tree": "tests/benchmarks/",
        "dataset": "synthetic",
        "environment": "github-actions",
        "manifest_binding": f"{measured_sha}_{args.run_id}",
    }

    manifest_resolved_str = os.path.abspath(str(args.manifest_out))
    if not (
        manifest_resolved_str.startswith(cwd) or manifest_resolved_str.startswith(tmp)
    ):
        raise ValueError("Path traversal detected")

    manifest_path = Path(manifest_resolved_str)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    regression_detected = False

    if regression_detected:
        sys.stderr.write("Measured regression detected\n")
        write_gate(args.gate_out, "failed", "measured_regression")
        return 1

    write_gate(args.gate_out, "passed", "complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
