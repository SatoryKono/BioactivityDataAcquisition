import argparse
import json
import os
import sys
from pathlib import Path
from scripts.engineering.common.repo_paths import confined_io_path


def validate_evidence(measurements_path: Path, expected_sha: str | None) -> dict:
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

    return manifest


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

    try:
        measurements_path = confined_io_path(
            args.measurements, allow_external_absolute=True
        )
        manifest_out = confined_io_path(args.manifest_out, allow_external_absolute=True)
    except ValueError as e:
        print(f"Path Traversal Error: {e}", file=sys.stderr)
        return 1

    try:
        manifest = validate_evidence(measurements_path, args.expected_sha)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Validation successful. Manifest written to {manifest_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
