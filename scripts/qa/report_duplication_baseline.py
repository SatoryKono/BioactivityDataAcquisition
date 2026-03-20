#!/usr/bin/env python3
"""Generate a report-only duplication baseline for composition/application seams.

Runs pylint duplicate-code scans for the requested targets, captures a stable
snapshot, and writes:
- machine-readable JSON summary
- markdown summary suitable for reviews and local artifacts

This is intentionally report-only. It does not fail on detected duplication;
it only fails when the underlying scan itself cannot be completed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_HEADER_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):\d+: R0801: Similar lines in 2 files$"
)
_MODULE_RE = re.compile(r"^==(?P<module>[^:]+):\[(?P<start>\d+):(?P<end>\d+)\]$")


@dataclass(frozen=True)
class DuplicateModuleRef:
    """One module/line-range reference inside a duplicate-code cluster."""

    module: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class DuplicateCluster:
    """Parsed duplicate-code finding from pylint output."""

    path: str
    line: int
    modules: tuple[DuplicateModuleRef, ...]


@dataclass(frozen=True)
class TargetDuplicationReport:
    """Summary for one scanned target path."""

    target: str
    returncode: int
    duplicate_count: int
    clusters: tuple[DuplicateCluster, ...]


def _parse_pylint_duplicate_output(stdout: str) -> list[DuplicateCluster]:
    """Parse pylint duplicate-code text output into structured clusters."""
    clusters: list[DuplicateCluster] = []
    current_path: str | None = None
    current_line: int | None = None
    current_modules: list[DuplicateModuleRef] = []

    def flush() -> None:
        nonlocal current_path, current_line, current_modules
        if current_path is None or current_line is None:
            current_path = None
            current_line = None
            current_modules = []
            return
        clusters.append(
            DuplicateCluster(
                path=current_path,
                line=current_line,
                modules=tuple(current_modules),
            )
        )
        current_path = None
        current_line = None
        current_modules = []

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        header_match = _HEADER_RE.match(line)
        if header_match is not None:
            flush()
            current_path = header_match.group("path")
            current_line = int(header_match.group("line"))
            continue

        module_match = _MODULE_RE.match(line)
        if module_match is not None and current_path is not None:
            current_modules.append(
                DuplicateModuleRef(
                    module=module_match.group("module"),
                    start_line=int(module_match.group("start")),
                    end_line=int(module_match.group("end")),
                )
            )
            continue

    flush()
    return clusters


def _scan_target(target: str, *, timeout_seconds: int) -> TargetDuplicationReport:
    """Run pylint duplicate-code scan for one target and parse findings."""
    cmd = [
        sys.executable,
        "-m",
        "pylint",
        "--disable=all",
        "--enable=duplicate-code",
        target,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    if result.returncode not in {0, 8}:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"unexpected return code {result.returncode}"
        raise RuntimeError(f"duplication scan failed for {target}: {details}")

    clusters = _parse_pylint_duplicate_output(result.stdout)
    return TargetDuplicationReport(
        target=target,
        returncode=result.returncode,
        duplicate_count=len(clusters),
        clusters=tuple(clusters),
    )


def _build_payload(
    reports: list[TargetDuplicationReport],
) -> dict[str, object]:
    """Build machine-readable payload for JSON output."""
    summary = {
        "targets": len(reports),
        "total_duplicate_clusters": sum(r.duplicate_count for r in reports),
    }
    return {
        "summary": summary,
        "targets": [
            {
                "target": report.target,
                "returncode": report.returncode,
                "duplicate_count": report.duplicate_count,
                "clusters": [
                    {
                        "path": cluster.path,
                        "line": cluster.line,
                        "modules": [asdict(module) for module in cluster.modules],
                    }
                    for cluster in report.clusters
                ],
            }
            for report in reports
        ],
    }


def _render_markdown(reports: list[TargetDuplicationReport]) -> str:
    """Render a compact markdown summary for review and local artifacts."""
    total = sum(r.duplicate_count for r in reports)
    lines = [
        "# Duplication Baseline Report",
        "",
        "- mode: report-only",
        f"- targets: {len(reports)}",
        f"- total_duplicate_clusters: {total}",
        "",
        "> Interpretation note: this is a visibility baseline. `R0801` can over-report",
        "> around facades, export barrels, and compatibility shims, so use it as",
        "> prioritization input rather than immediate blocking debt.",
        "",
        "| Target | Duplicate clusters |",
        "| --- | ---: |",
    ]
    for report in reports:
        lines.append(f"| `{report.target}` | {report.duplicate_count} |")

    for report in reports:
        lines.extend(
            [
                "",
                f"## {report.target}",
                "",
                f"- duplicate clusters: {report.duplicate_count}",
            ]
        )
        if not report.clusters:
            lines.append("- no `R0801` findings")
            continue
        lines.extend(
            [
                "",
                "| Cluster path | Compared modules |",
                "| --- | --- |",
            ]
        )
        for cluster in report.clusters[:12]:
            module_summary = ", ".join(
                f"`{m.module}`[{m.start_line}:{m.end_line}]"
                for m in cluster.modules[:2]
            )
            lines.append(f"| `{cluster.path}:{cluster.line}` | {module_summary} |")
        if len(report.clusters) > 12:
            lines.append(
                f"\n- … truncated {len(report.clusters) - 12} additional clusters for brevity"
            )

    lines.append("")
    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--targets",
        nargs="+",
        default=["src/bioetl/composition", "src/bioetl/application"],
        help="Target paths to scan with pylint duplicate-code.",
    )
    parser.add_argument(
        "--json-out",
        default="reports/quality/duplication-baseline.json",
        help="Path for machine-readable JSON output.",
    )
    parser.add_argument(
        "--md-out",
        default="reports/quality/duplication-baseline.md",
        help="Path for markdown summary output.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=90,
        help="Per-target timeout for pylint duplicate-code scans.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    reports = [
        _scan_target(target, timeout_seconds=args.timeout_seconds)
        for target in args.targets
    ]

    payload = _build_payload(reports)
    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    _write_text(json_path, json.dumps(payload, ensure_ascii=True, indent=2) + "\n")
    _write_text(md_path, _render_markdown(reports))

    total = sum(report.duplicate_count for report in reports)
    print(
        "[duplication-baseline] "
        f"targets={len(reports)}; total_duplicate_clusters={total}; "
        f"json={json_path}; markdown={md_path}"
    )
    for report in reports:
        print(
            "[duplication-baseline] "
            f"target={report.target}; duplicate_clusters={report.duplicate_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
