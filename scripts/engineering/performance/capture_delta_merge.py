"""Capture sequential Delta merges with raw GNU time output and source identity.

Run from a clean source checkout with its prepared Python environment:
python /path/to/capture_delta_merge.py --output-dir /path/to/new/run
GITHUB_SHA, when present, must match HEAD. Local runs record it as null.
Existing evidence directories are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _time_metrics(raw: str) -> tuple[str, int]:
    wall = rss = None
    for line in raw.splitlines():
        if line.strip().startswith("Elapsed (wall clock) time"):
            wall = line.rsplit(": ", 1)[1].strip()
        if line.strip().startswith("Maximum resident set size (kbytes):"):
            rss = int(line.rsplit(":", 1)[1])
    if wall is None or rss is None:
        raise ValueError("GNU time output is missing wall time or peak RSS")
    return wall, rss


def _capture(n: int, output: Path, revision: str) -> dict:
    directory = output / f"N{n}"
    directory.mkdir()
    timing = directory / "time.txt"
    log = directory / "pytest.log"
    command = [
        "/usr/bin/time",
        "-v",
        "-o",
        str(timing),
        sys.executable,
        "-m",
        "pytest",
        f"tests/performance/test_delta_sequential_merge.py::test_delta_sequential_merge_scaling[{n}]",
        f"--delta-merge-report-dir={directory}",
    ]
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command,
            stdout=stream,
            stderr=subprocess.STDOUT,
            env={**os.environ, "LC_ALL": "C"},
            check=False,
        )
    row = {
        "n_merges": n,
        "source_revision": revision,
        "command": command,
        "exit_code": result.returncode,
        "status": "failed",
    }
    try:
        wall, rss = _time_metrics(timing.read_text(encoding="utf-8"))
        row.update(wall_time=wall, peak_rss_kb=rss)
        if result.returncode != 0:
            raise ValueError(f"pytest exited with {result.returncode}")
        summaries = list(directory.glob(f"N{n}-*/merge_scaling_N{n}.json"))
        if len(summaries) != 1:
            raise ValueError(
                "Expected exactly one complete merge summary (test may have skipped)"
            )
        summary = json.loads(summaries[0].read_text(encoding="utf-8"))
        if (
            summary["status"] != "complete"
            or summary["n_merges_target"] != n
            or summary["n_merges_completed"] != n
            or len(summary["merges"]) != n
            or summary["actual_final_rows"] != summary["expected_final_rows"]
        ):
            raise ValueError(
                "Merge summary is incomplete or has inconsistent row outcomes"
            )
        row.update(
            status="complete",
            merge_time_sum_s=sum(
                item["merge_time_raw_s"] for item in summary["merges"]
            ),
            final_rows=summary["actual_final_rows"],
            processed_rows=summary["total_records_processed"],
        )
    except (ValueError, KeyError, OSError) as exc:
        row["error"] = str(exc)
    row["artifacts_sha256"] = {
        path.relative_to(output).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix != ".lock"
    }
    return row


def render_markdown(manifest: dict) -> str:
    """Generate a table from the measured summaries and preserved time output."""
    lines = [
        "# Benchmark Provenance Report",
        "",
        f"Source revision: `{manifest['source_revision']}` (clean Git checkout).",
        "Full GNU time output, pytest logs and JSON summaries for each N are",
        "bound by SHA-256 in `manifest.json`; raw timing output is in `N<N>/time.txt`.",
        "",
        "| N | SHA | Command | Wall Time | Merge Time Sum | Peak RSS | Final Rows | Processed Rows |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in manifest["runs"]:
        if row["status"] != "complete":
            lines.extend(
                [
                    "",
                    f"N={row['n_merges']} failed: see `manifest.json` and its raw artifacts.",
                ]
            )
            continue
        lines.append(
            f"| {row['n_merges']} | {row['source_revision']} | `{shlex.join(row['command'])}` "
            f"| {row['wall_time']} | {row['merge_time_sum_s']:.4f}s "
            f"| {row['peak_rss_kb']} KB | {row['final_rows']} | {row['processed_rows']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--n", type=int, nargs="+", choices=(10, 50, 100), default=[10, 50, 100]
    )
    args = parser.parse_args(argv)
    revision = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain", "--untracked-files=all"):
        parser.error("Benchmark source checkout must be clean")
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha and github_sha != revision:
        parser.error("GITHUB_SHA does not match the source checkout HEAD")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": 1,
        "source_revision": revision,
        "github_sha": github_sha,
        "revision_method": "git_rev_parse_HEAD",
        "source_worktree_clean": True,
        "captured_at": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "capture_script_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "uv_lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "runs": [],
    }
    for n in dict.fromkeys(args.n):
        manifest["runs"].append(_capture(n, output, revision))
        (output / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        (output / "benchmark_provenance.md").write_text(
            render_markdown(manifest), encoding="utf-8"
        )
    return int(any(row["status"] != "complete" for row in manifest["runs"]))


if __name__ == "__main__":
    raise SystemExit(main())
