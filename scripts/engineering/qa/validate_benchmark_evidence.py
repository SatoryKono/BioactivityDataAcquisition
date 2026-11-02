import argparse
import json
import os
import sys
from pathlib import Path
from scripts.engineering.common.repo_paths import confined_io_path


def validate_evidence(
    measurements_path: Path,
    expected_sha: str | None,
    *,
    producer_outcome: str,
    environ: dict | None = None,
    _root: Path | None = None,
) -> dict:
    if producer_outcome != "success":
        raise ValueError(f"Benchmark producer did not succeed: {producer_outcome}")
    if not measurements_path.exists():
        raise ValueError(f"Missing observations: {measurements_path} not found")

    if measurements_path.stat().st_size == 0:
        raise ValueError(f"Empty JSON in {measurements_path}")

    try:
        data = json.loads(measurements_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {measurements_path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid JSON structure in {measurements_path}: expected dict"
        )

    benchmarks = data.get("benchmarks", [])
    if not benchmarks:
        raise ValueError("Zero execution or all-skipped (no benchmarks found)")

    for b in benchmarks:
        # pytest-benchmark records failures or errors
        if b.get("has_error", False):
            raise ValueError(f"Failed benchmark detected: {b.get('name', 'unknown')}")

    commit_info = data.get("commit_info", {})
    actual_sha = commit_info.get("id")
    if not actual_sha:
        raise ValueError(
            "No commit SHA found in benchmark JSON (commit_info.id missing)"
        )

    if expected_sha and actual_sha != expected_sha:
        raise ValueError(f"Wrong SHA. Expected {expected_sha}, got {actual_sha}")

    machine_info = data.get("machine_info", {})

    # Extract identity
    manifest = {
        "revision": actual_sha,
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "run_url": f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', 'local/repo')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', 'local')}/attempts/{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}",
        "environment_identity": machine_info,
        "dataset_identity": "unknown",  # default placeholder as dataset isn't explicitly bound yet
        "benchmarks_count": len(benchmarks),
    }

    # We update missing test data that fails later tests if not present
    if environ is None:
        environ = dict(os.environ)
    if environ.get("GITHUB_ACTIONS") != "true":
        manifest["run_id"] = "local"
        manifest["run_url"] = None
        manifest["environment"] = "local"
    else:
        manifest["run_id"] = environ.get("GITHUB_RUN_ID", "")
        manifest["run_attempt"] = environ.get("GITHUB_RUN_ATTEMPT", "")
        repository = environ.get("GITHUB_REPOSITORY", "")
        manifest["run_url"] = f"https://github.com/{repository}/actions/runs/{manifest['run_id']}/attempts/{manifest['run_attempt']}"
        manifest["environment"] = "github-actions"

    return manifest


def validate_benchmark_evidence_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate benchmark evidence.")
    parser.add_argument(
        "--measurements",
        type=Path,
        default=Path("reports/performance/benchmark-measurements.json"),
    )
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=Path("reports/performance/benchmark-manifest.json"),
    )
    parser.add_argument(
        "--expected-sha", type=str, default=os.environ.get("GITHUB_SHA")
    )
    parser.add_argument("--producer-outcome", required=False)
    parser.add_argument("--contract-outcome", required=False)
    parser.add_argument("--failure-manifest-out", type=Path)
    parser.add_argument("--failure-gate-out", type=Path)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        if getattr(args, "output_root", None):
            measurements_path = confined_io_path(
                args.measurements, root=args.output_root
            )
            manifest_out = confined_io_path(
                args.manifest_out, root=args.output_root
            )
        else:
            measurements_path = confined_io_path(
                args.measurements, allow_external_absolute=True
            )
            manifest_out = confined_io_path(
                args.manifest_out, allow_external_absolute=True
            )
    except ValueError as e:
        print(f"Path Traversal Error: {e}", file=sys.stderr)
        return 1

    try:
        if getattr(args, "contract_outcome", "success") != "success":
            raise ValueError(f"Benchmark measurement contract did not succeed: {args.contract_outcome}")
        manifest = validate_evidence(
            measurements_path, args.expected_sha, producer_outcome=getattr(args, "producer_outcome", "success"), _root=getattr(args, "output_root", None)
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        try:
            if manifest_out.exists():
                manifest_out.unlink()
        except OSError:
            pass

        import json
        failure_payload = {
            "schema_version": 1,
            "status": "failed",
            "reason": str(e),
            "producer_outcome": getattr(args, "producer_outcome", "success") or "success",
            "contract_outcome": getattr(args, "contract_outcome", "success") or "success"
        }

        if getattr(args, "failure_manifest_out", None):
            failure_manifest = confined_io_path(args.failure_manifest_out, root=args.output_root) if getattr(args, "output_root", None) else confined_io_path(args.failure_manifest_out, allow_external_absolute=True)
            failure_manifest.parent.mkdir(parents=True, exist_ok=True)
            failure_manifest.write_text(json.dumps(failure_payload) + "\n")
        if getattr(args, "failure_gate_out", None):
            failure_gate = confined_io_path(args.failure_gate_out, root=args.output_root) if getattr(args, "output_root", None) else confined_io_path(args.failure_gate_out, allow_external_absolute=True)
            failure_gate.parent.mkdir(parents=True, exist_ok=True)
            failure_gate.write_text(json.dumps(failure_payload) + "\n")
        return 1

    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Validation successful. Manifest written to {manifest_out}")
    return 0


if __name__ == "__main__":
    sys.exit(validate_benchmark_evidence_main())

main = validate_benchmark_evidence_main
