#!/usr/bin/env python3
"""Generate duplication baseline and optional zero-ratchet checks.

Runs pylint duplicate-code scans for the requested targets, captures a stable
snapshot, and writes:
- machine-readable JSON summary
- markdown summary suitable for reviews and local artifacts

By default this writes report artifacts and fails only when a scan cannot be
completed. Release/CI gates can pass ``--max-duplicate-clusters`` to make the
same deterministic scan fail fast on reviewed hotspot duplication growth.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
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
    raw_duplicate_count: int | None = None


_LOW_RISK_ACTIONABILITY_CATEGORIES = frozenset(
    {
        "cli_command_contract_shell",
        "composition_runtime_wiring_pattern",
        "export_facade_or_package_barrel",
    }
)


def _zero_actionability_category(target: str) -> str | None:
    """Return the reviewed zero-duplication category for governed targets."""
    normalized_target = target.replace("\\", "/").rstrip("/")
    if normalized_target.endswith("src/bioetl/interfaces/cli"):
        return "cli_command_contract_shell"
    return None


def _is_self_module_cluster(cluster: DuplicateCluster) -> bool:
    """Return True when a finding only restates the same module against itself.

    Pylint duplicate-code occasionally emits same-module pairs for facade /
    barrel surfaces; those are noise for hotspot residual-debt ratchets.
    """
    module_names = {module.module for module in cluster.modules}
    return len(module_names) <= 1


def _is_package_entry_report_noise(cluster: DuplicateCluster) -> bool:
    """Return True when pylint attributes multi-module dupes to a package ``__init__``.

    Pylint sometimes reports the comparison path as a package entry module even
    when neither compared module is that package root. Those findings are not
    actionable residual debt for hotspot family ratchets.

    Linux pylint often attributes the same thin fetch-signature shells to one of
    the concrete modules instead of ``__init__.py``; treat those known
    application.core fetch-contract pairs as wiring noise as well.
    """
    module_names = {module.module for module in cluster.modules}
    normalized_path = cluster.path.replace("\\", "/")
    if normalized_path.endswith("/__init__.py") and not any(
        module.endswith(".__init__") for module in module_names
    ):
        return True
    core_fetch_shells = {
        "bioetl.application.core._fetch_forwarding",
        "bioetl.application.core.filtered_data_source_mixins",
        "bioetl.application.core.target_data_source_mixins",
    }
    return module_names <= core_fetch_shells and len(module_names) >= 2


def _cluster_actionability_category(cluster: DuplicateCluster) -> str:
    """Classify duplicate-code findings by likely remediation path."""
    module_names = [module.module for module in cluster.modules]
    if _is_self_module_cluster(cluster):
        return "self_module_scanner_noise"
    if _is_package_entry_report_noise(cluster):
        return "package_entry_report_noise"
    normalized_path = cluster.path.replace("\\", "/")
    if any(
        token in module
        for module in module_names
        for token in ("fallback", "resilience", "health_check_contract")
    ):
        return "adapter_resilience_or_contract_template"
    if any(".interfaces.cli." in module for module in module_names):
        return "cli_command_contract_shell"
    if any(".application.pipelines." in module for module in module_names):
        return "pipeline_transformer_contract_pattern"
    if any(".composition." in module for module in module_names):
        return "composition_runtime_wiring_pattern"
    if normalized_path.endswith("/__init__.py") or any(
        module.endswith(".__init__") for module in module_names
    ):
        return "export_facade_or_package_barrel"
    return "behavior_bearing_candidate"


def _actionability_summary(
    target: str,
    clusters: tuple[DuplicateCluster, ...],
) -> list[dict[str, object]]:
    """Return deterministic actionability counts for report triage."""
    counts = Counter(_cluster_actionability_category(cluster) for cluster in clusters)
    if not counts:
        zero_category = _zero_actionability_category(target)
        if zero_category is not None:
            return [
                {
                    "category": zero_category,
                    "duplicate_clusters": 0,
                }
            ]
    return [
        {
            "category": category,
            "duplicate_clusters": count,
        }
        for category, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def _top_duplicate_pairs(
    clusters: tuple[DuplicateCluster, ...],
    *,
    limit: int = 5,
) -> list[dict[str, object]]:
    """Summarize the most frequently repeated module pairs for prioritization."""
    pair_counts: dict[tuple[str, str], int] = {}
    for cluster in clusters:
        modules = [module.module for module in cluster.modules[:2]]
        if len(modules) < 2:
            continue
        pair = tuple(sorted(modules))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1

    ranked = sorted(
        pair_counts.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    )
    return [
        {
            "modules": [left, right],
            "duplicate_clusters": count,
        }
        for (left, right), count in ranked[:limit]
    ]


def _build_reduction_leverage_ranking(
    reports: list[TargetDuplicationReport],
) -> list[dict[str, object]]:
    """Rank targets by first-wave reduction leverage using current report evidence."""
    ranking_rows: list[dict[str, object]] = []
    for report in reports:
        category_counts = Counter(
            {
                str(item["category"]): int(item["duplicate_clusters"])
                for item in _actionability_summary(report.target, report.clusters)
                if isinstance(item.get("category"), str)
                and isinstance(item.get("duplicate_clusters"), int)
            }
        )
        dominant_category = None
        dominant_count = 0
        if category_counts:
            dominant_category, dominant_count = sorted(
                category_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[0]
        low_risk_cluster_count = sum(
            count
            for category, count in category_counts.items()
            if category in _LOW_RISK_ACTIONABILITY_CATEGORIES
        )
        low_risk_share = (
            round(low_risk_cluster_count / report.duplicate_count, 4)
            if report.duplicate_count
            else 0.0
        )
        recommended_first_wave = (
            report.duplicate_count > 0
            and dominant_category in _LOW_RISK_ACTIONABILITY_CATEGORIES
            and report.duplicate_count <= 25
        )
        ranking_rows.append(
            {
                "target": report.target,
                "duplicate_clusters": report.duplicate_count,
                "dominant_actionability_category": dominant_category,
                "dominant_actionability_cluster_count": dominant_count,
                "low_risk_cluster_count": low_risk_cluster_count,
                "low_risk_cluster_share": low_risk_share,
                "recommended_first_wave": recommended_first_wave,
            }
        )
    return sorted(
        ranking_rows,
        key=lambda row: (
            not bool(row["recommended_first_wave"]),
            -float(row["low_risk_cluster_share"]),
            -int(row["duplicate_clusters"]),
            str(row["target"]),
        ),
    )


def _build_first_wave_selection(
    ranking_rows: list[dict[str, object]],
) -> dict[str, object]:
    """Select the best current first-wave target from the reduction ranking."""
    if not ranking_rows:
        return {"status": "no_targets"}

    selected = ranking_rows[0]
    return {
        "status": "selected",
        "target": selected["target"],
        "duplicate_clusters": selected["duplicate_clusters"],
        "dominant_actionability_category": selected["dominant_actionability_category"],
        "selection_rule": (
            "prefer low-risk actionability families with bounded cluster counts, "
            "then maximize duplicate reduction leverage"
        ),
    }


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

    flush()
    return clusters


def _compile_patterns(raw_patterns: list[str]) -> tuple[re.Pattern[str], ...]:
    """Compile user-provided regex patterns once for reuse."""
    return tuple(re.compile(pattern) for pattern in raw_patterns)


def _filter_clusters_by_module_patterns(
    clusters: list[DuplicateCluster],
    *,
    exclude_module_patterns: tuple[re.Pattern[str], ...],
) -> list[DuplicateCluster]:
    """Drop clusters involving explicitly normalized module patterns."""
    if not exclude_module_patterns:
        return clusters

    filtered: list[DuplicateCluster] = []
    for cluster in clusters:
        if any(
            pattern.search(module.module)
            for pattern in exclude_module_patterns
            for module in cluster.modules
        ):
            continue
        filtered.append(cluster)
    return filtered


def _filter_clusters_by_actionability_categories(
    clusters: list[DuplicateCluster],
    *,
    exclude_actionability_categories: frozenset[str],
) -> list[DuplicateCluster]:
    """Drop clusters whose reviewed actionability category is normalized away."""
    if not exclude_actionability_categories:
        return clusters
    return [
        cluster
        for cluster in clusters
        if _cluster_actionability_category(cluster)
        not in exclude_actionability_categories
    ]


def _load_history_records(
    path: Path, *, root: Path | None = None
) -> list[dict[str, object]]:
    """Load prior JSONL history records when present."""
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _build_trend_summary(
    *,
    history_records: list[dict[str, object]],
    current_targets: list[dict[str, object]],
    snapshot_date: str,
    total_duplicate_clusters: int,
) -> dict[str, object]:
    """Compare current snapshot against the most recent prior observation."""
    if not history_records:
        return {"status": "no_prior_snapshot", "snapshot_date": snapshot_date}

    previous = _previous_history_record(history_records, snapshot_date=snapshot_date)
    if previous is None:
        return {"status": "no_prior_distinct_snapshot", "snapshot_date": snapshot_date}

    previous_summary = previous.get("summary", {})
    previous_targets = _previous_target_map(previous.get("targets", []))
    comparison_rows = _comparison_rows(
        current_targets,
        previous_targets=previous_targets,
    )

    previous_total = previous_summary.get("total_duplicate_clusters")
    total_delta = (
        total_duplicate_clusters - previous_total
        if isinstance(previous_total, int)
        else None
    )
    previous_snapshot_date = previous.get("snapshot_date") or previous_summary.get(
        "snapshot_date"
    )
    return {
        "status": "compared_to_previous",
        "snapshot_date": snapshot_date,
        "previous_snapshot_date": previous_snapshot_date,
        "total_duplicate_cluster_delta": total_delta,
        "targets": comparison_rows,
    }


def _previous_history_record(
    history_records: list[dict[str, object]],
    *,
    snapshot_date: str,
) -> dict[str, object] | None:
    """Return the most recent prior snapshot with a different date label."""
    for candidate in reversed(history_records):
        if candidate.get("snapshot_date") != snapshot_date:
            return candidate
    return None


def _previous_target_map(
    previous_targets_raw: object,
) -> dict[str, dict[str, object]]:
    """Build a lookup of prior target summaries by target path."""
    if not isinstance(previous_targets_raw, list):
        return {}
    return {
        item.get("target"): item
        for item in previous_targets_raw
        if isinstance(item, dict) and isinstance(item.get("target"), str)
    }


def _comparison_row(
    item: dict[str, object],
    *,
    previous_targets: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    """Build one comparison row when the target payload is valid."""
    target = item.get("target")
    current_count = item.get("duplicate_count")
    if not isinstance(target, str) or not isinstance(current_count, int):
        return None
    previous_item = previous_targets.get(target)
    previous_count = (
        previous_item.get("duplicate_count")
        if isinstance(previous_item, dict)
        and isinstance(previous_item.get("duplicate_count"), int)
        else None
    )
    return {
        "target": target,
        "current_duplicate_count": current_count,
        "previous_duplicate_count": previous_count,
        "delta_duplicate_count": (
            current_count - previous_count if previous_count is not None else None
        ),
    }


def _comparison_rows(
    current_targets: list[dict[str, object]],
    *,
    previous_targets: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Build comparison rows against the previous snapshot."""
    rows: list[dict[str, object]] = []
    for item in current_targets:
        row = _comparison_row(item, previous_targets=previous_targets)
        if row is not None:
            rows.append(row)
    return rows


def _scan_target(
    target: str,
    *,
    timeout_seconds: int,
    exclude_module_patterns: tuple[re.Pattern[str], ...] = (),
    exclude_actionability_categories: frozenset[str] = frozenset(),
) -> TargetDuplicationReport:
    """Run pylint duplicate-code scan for one target and parse findings."""
    cmd = [
        sys.executable,
        "-m",
        "pylint",
        "--disable=all",
        "--enable=duplicate-code",
        target,
    ]
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    result = subprocess.run(
        ensure_safe_cli_argv([str(token) for token in cmd]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout_seconds,
    )
    if result.returncode not in {0, 8}:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"unexpected return code {result.returncode}"
        raise RuntimeError(f"duplication scan failed for {target}: {details}")

    raw_clusters = _parse_pylint_duplicate_output(result.stdout)
    clusters = _filter_clusters_by_module_patterns(
        raw_clusters,
        exclude_module_patterns=exclude_module_patterns,
    )
    # Drop same-module self-pairs and package-entry report noise before
    # actionability filters so hotspot family residual counts only include
    # multi-module structural findings.
    clusters = [
        cluster
        for cluster in clusters
        if not _is_self_module_cluster(cluster)
        and not _is_package_entry_report_noise(cluster)
    ]
    clusters = _filter_clusters_by_actionability_categories(
        clusters,
        exclude_actionability_categories=exclude_actionability_categories,
    )
    return TargetDuplicationReport(
        target=target,
        returncode=result.returncode,
        duplicate_count=len(clusters),
        clusters=tuple(clusters),
        raw_duplicate_count=len(raw_clusters),
    )


def _build_payload(
    reports: list[TargetDuplicationReport],
    *,
    snapshot_date: str,
    exclude_module_patterns: list[str],
    exclude_actionability_categories: list[str],
    trend_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build machine-readable payload for JSON output."""
    total_duplicate_clusters = sum(r.duplicate_count for r in reports)
    total_raw_duplicate_clusters = sum(
        r.raw_duplicate_count
        if r.raw_duplicate_count is not None
        else r.duplicate_count
        for r in reports
    )
    summary = {
        "snapshot_date": snapshot_date,
        "targets": len(reports),
        "total_duplicate_clusters": total_duplicate_clusters,
        "total_raw_duplicate_clusters": total_raw_duplicate_clusters,
        "total_excluded_duplicate_clusters": total_raw_duplicate_clusters
        - total_duplicate_clusters,
    }
    reduction_ranking = _build_reduction_leverage_ranking(reports)
    return {
        "summary": summary,
        "normalization": {
            "exclude_module_patterns": exclude_module_patterns,
            "exclude_actionability_categories": exclude_actionability_categories,
        },
        "trend": trend_summary or {"status": "no_prior_snapshot"},
        "reduction_leverage_ranking": reduction_ranking,
        "first_wave": _build_first_wave_selection(reduction_ranking),
        "targets": [
            {
                "target": report.target,
                "returncode": report.returncode,
                "duplicate_count": report.duplicate_count,
                "raw_duplicate_count": (
                    report.raw_duplicate_count
                    if report.raw_duplicate_count is not None
                    else report.duplicate_count
                ),
                "excluded_duplicate_count": (
                    (
                        report.raw_duplicate_count
                        if report.raw_duplicate_count is not None
                        else report.duplicate_count
                    )
                    - report.duplicate_count
                ),
                "actionability": _actionability_summary(
                    report.target,
                    report.clusters,
                ),
                "top_pairs": _top_duplicate_pairs(report.clusters),
                "clusters": [
                    {
                        "path": cluster.path,
                        "line": cluster.line,
                        "actionability_category": _cluster_actionability_category(
                            cluster
                        ),
                        "modules": [asdict(module) for module in cluster.modules],
                    }
                    for cluster in report.clusters
                ],
            }
            for report in reports
        ],
    }


def _render_markdown(
    reports: list[TargetDuplicationReport],
    *,
    exclude_module_patterns: tuple[str, ...] = (),
    exclude_actionability_categories: tuple[str, ...] = (),
    trend_summary: dict[str, object] | None = None,
    max_duplicate_clusters: int | None = None,
) -> str:
    """Render a compact markdown summary for review and local artifacts."""
    total = sum(r.duplicate_count for r in reports)
    raw_total = sum(
        r.raw_duplicate_count
        if r.raw_duplicate_count is not None
        else r.duplicate_count
        for r in reports
    )
    lines = _markdown_summary_lines(
        reports,
        total=total,
        raw_total=raw_total,
        exclude_module_patterns=exclude_module_patterns,
        exclude_actionability_categories=exclude_actionability_categories,
        trend_summary=trend_summary,
        max_duplicate_clusters=max_duplicate_clusters,
    )
    for report in reports:
        lines.append(f"| `{report.target}` | {report.duplicate_count} |")

    for report in reports:
        lines.extend(_report_markdown_section(report))

    lines.extend(_trend_markdown_section(trend_summary))
    lines.extend(_reduction_ranking_markdown_section(reports))

    lines.append("")
    return "\n".join(lines)


def _markdown_summary_lines(
    reports: list[TargetDuplicationReport],
    *,
    total: int,
    raw_total: int,
    exclude_module_patterns: tuple[str, ...],
    exclude_actionability_categories: tuple[str, ...],
    trend_summary: dict[str, object] | None,
    max_duplicate_clusters: int | None,
) -> list[str]:
    """Render top-of-report summary bullets and table header."""
    mode = "fail-fast" if max_duplicate_clusters is not None else "report-only"
    lines = [
        "# Duplication Baseline Report",
        "",
        f"- mode: {mode}",
        f"- targets: {len(reports)}",
        f"- total_duplicate_clusters: {total}",
    ]
    if max_duplicate_clusters is not None:
        lines.append(f"- max_duplicate_clusters: {max_duplicate_clusters}")
    if exclude_module_patterns or exclude_actionability_categories:
        lines.extend(
            [
                f"- total_raw_duplicate_clusters: {raw_total}",
                f"- excluded_duplicate_clusters: {raw_total - total}",
                "- normalized_view: enabled",
            ]
        )
        if exclude_module_patterns:
            lines.append(
                "- exclude_module_patterns: "
                + ", ".join(f"`{pattern}`" for pattern in exclude_module_patterns)
            )
        if exclude_actionability_categories:
            lines.append(
                "- exclude_actionability_categories: "
                + ", ".join(
                    f"`{category}`" for category in exclude_actionability_categories
                )
            )
    if trend_summary and trend_summary.get("status") == "compared_to_previous":
        raw_delta = trend_summary.get("total_duplicate_cluster_delta")
        delta_text = f"{raw_delta:+d}" if isinstance(raw_delta, int) else "n/a"
        lines.extend(
            [
                f"- previous_snapshot_date: {trend_summary.get('previous_snapshot_date')}",
                f"- total_duplicate_cluster_delta_vs_previous: {delta_text}",
            ]
        )
    lines.extend(
        [
            "",
            "> Interpretation note: this is a visibility baseline. `R0801` can over-report",
            "> around facades, export barrels, and compatibility shims, so use it as",
            "> prioritization input rather than immediate blocking debt.",
            "",
            "| Target | Duplicate clusters |",
            "| --- | ---: |",
        ]
    )
    return lines


def _actionability_markdown_section(report: TargetDuplicationReport) -> list[str]:
    """Render actionability counts for one target."""
    summary = _actionability_summary(report.target, report.clusters)
    if not summary:
        return []
    lines = [
        "",
        "| Actionability category | Duplicate clusters |",
        "| --- | ---: |",
    ]
    for row in summary:
        category = row.get("category")
        count = row.get("duplicate_clusters")
        if isinstance(category, str) and isinstance(count, int):
            lines.append(f"| `{category}` | {count} |")
    return lines


def _reduction_ranking_markdown_section(
    reports: list[TargetDuplicationReport],
) -> list[str]:
    ranking_rows = _build_reduction_leverage_ranking(reports)
    first_wave = _build_first_wave_selection(ranking_rows)
    lines = [
        "",
        "## Reduction Leverage Ranking",
        "",
        "| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for row in ranking_rows:
        lines.append(
            f"| `{row['target']}` | {row['duplicate_clusters']} | "
            f"`{row['dominant_actionability_category'] or 'n/a'}` | "
            f"{float(row['low_risk_cluster_share']):.2f} | "
            f"{'yes' if row['recommended_first_wave'] else 'no'} |"
        )
    if first_wave.get("status") == "selected":
        lines.extend(
            [
                "",
                "## First Wave Selection",
                "",
                f"- target: `{first_wave['target']}`",
                f"- duplicate_clusters: {first_wave['duplicate_clusters']}",
                "- dominant_actionability_category: "
                f"`{first_wave['dominant_actionability_category']}`",
                f"- selection_rule: {first_wave['selection_rule']}",
            ]
        )
    return lines


def _top_pairs_markdown_section(report: TargetDuplicationReport) -> list[str]:
    """Render top recurring pair table when available."""
    top_pairs = _top_duplicate_pairs(report.clusters)
    if not top_pairs:
        return []
    lines = [
        "",
        "| Top recurring module pairs | Duplicate clusters |",
        "| --- | ---: |",
    ]
    for item in top_pairs:
        modules = item.get("modules", [])
        count = item.get("duplicate_clusters")
        if (
            isinstance(modules, list)
            and len(modules) == 2
            and isinstance(modules[0], str)
            and isinstance(modules[1], str)
            and isinstance(count, int)
        ):
            lines.append(f"| `{modules[0]}` <-> `{modules[1]}` | {count} |")
    return lines


def _report_markdown_section(report: TargetDuplicationReport) -> list[str]:
    """Render one per-target markdown section."""
    lines = [
        "",
        f"## {report.target}",
        "",
        f"- duplicate clusters: {report.duplicate_count}",
    ]
    raw_duplicate_count = (
        report.raw_duplicate_count
        if report.raw_duplicate_count is not None
        else report.duplicate_count
    )
    if raw_duplicate_count != report.duplicate_count:
        lines.extend(
            [
                f"- raw duplicate clusters: {raw_duplicate_count}",
                f"- excluded duplicate clusters: "
                f"{raw_duplicate_count - report.duplicate_count}",
            ]
        )
    lines.extend(_actionability_markdown_section(report))
    lines.extend(_top_pairs_markdown_section(report))
    if not report.clusters:
        lines.append("- no `R0801` findings")
        return lines
    lines.extend(
        [
            "",
            "| Cluster path | Compared modules |",
            "| --- | --- |",
        ]
    )
    for cluster in report.clusters[:12]:
        module_summary = ", ".join(
            f"`{m.module}`[{m.start_line}:{m.end_line}]" for m in cluster.modules[:2]
        )
        lines.append(f"| `{cluster.path}:{cluster.line}` | {module_summary} |")
    if len(report.clusters) > 12:
        lines.append(
            f"\n- … truncated {len(report.clusters) - 12} additional clusters for brevity"
        )
    return lines


def _trend_markdown_row(item: object) -> str | None:
    """Render one trend row when the payload is valid."""
    if not isinstance(item, dict):
        return None
    target = item.get("target")
    current_count = item.get("current_duplicate_count")
    previous_count = item.get("previous_duplicate_count")
    delta = item.get("delta_duplicate_count")
    if not isinstance(target, str) or not isinstance(current_count, int):
        return None
    previous_text = str(previous_count) if isinstance(previous_count, int) else "n/a"
    delta_text = f"{delta:+d}" if isinstance(delta, int) else "n/a"
    return f"| `{target}` | {current_count} | {previous_text} | {delta_text} |"


def _trend_markdown_section(trend_summary: dict[str, object] | None) -> list[str]:
    """Render trend comparison section when available."""
    if not trend_summary or trend_summary.get("status") != "compared_to_previous":
        return []
    raw_delta = trend_summary.get("total_duplicate_cluster_delta")
    delta_text = f"{raw_delta:+d}" if isinstance(raw_delta, int) else "n/a"
    lines = [
        "",
        "## Trend vs Previous Snapshot",
        "",
        f"- previous snapshot: `{trend_summary.get('previous_snapshot_date')}`",
        f"- total duplicate cluster delta: {delta_text}",
        "",
        "| Target | Current | Previous | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    target_rows = trend_summary.get("targets", [])
    if isinstance(target_rows, list):
        for item in target_rows:
            row = _trend_markdown_row(item)
            if row is not None:
                lines.append(row)
    return lines


def _write_text(path: Path, content: str, *, root: Path | None = None) -> None:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _append_history_jsonl(
    path: Path, *, payload: dict[str, object], root: Path | None = None
) -> None:
    """Append a compact observation record for later trend comparisons."""
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    targets = payload.get("targets", [])
    record = {
        "snapshot_date": payload.get("summary", {}).get("snapshot_date"),
        "summary": payload.get("summary", {}),
        "normalization": payload.get("normalization", {}),
        "targets": [
            {
                "target": item.get("target"),
                "duplicate_count": item.get("duplicate_count"),
                "raw_duplicate_count": item.get("raw_duplicate_count"),
                "excluded_duplicate_count": item.get("excluded_duplicate_count"),
            }
            for item in targets
            if isinstance(item, dict)
        ],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


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
    parser.add_argument(
        "--exclude-module-pattern",
        action="append",
        default=[],
        help=(
            "Regex for module names to exclude from the normalized view. "
            "Raw counts remain in the JSON payload."
        ),
    )
    parser.add_argument(
        "--exclude-actionability-category",
        action="append",
        default=[],
        help=(
            "Reviewed actionability category to exclude from normalized counts. "
            "Raw counts remain in the JSON payload."
        ),
    )
    parser.add_argument(
        "--history-jsonl",
        default=None,
        help="Optional append-only JSONL history file for trend snapshots.",
    )
    parser.add_argument(
        "--snapshot-date",
        default=None,
        help="Optional snapshot date label (defaults to today in ISO format).",
    )
    parser.add_argument(
        "--max-duplicate-clusters",
        type=int,
        default=None,
        help=(
            "Fail when the normalized total duplicate cluster count exceeds this "
            "budget. Omit for report-only artifact generation."
        ),
    )
    return parser.parse_args()


def main() -> int:
    from scripts.engineering.common.repo_paths import REPO_ROOT

    args = _parse_args()
    root = REPO_ROOT
    snapshot_date = args.snapshot_date or date.today().isoformat()
    exclude_module_patterns = _compile_patterns(args.exclude_module_pattern)
    reports = [
        _scan_target(
            target,
            timeout_seconds=args.timeout_seconds,
            exclude_module_patterns=exclude_module_patterns,
            exclude_actionability_categories=frozenset(
                str(category) for category in args.exclude_actionability_category
            ),
        )
        for target in args.targets
    ]
    target_rows = [
        {
            "target": report.target,
            "duplicate_count": report.duplicate_count,
            "raw_duplicate_count": (
                report.raw_duplicate_count
                if report.raw_duplicate_count is not None
                else report.duplicate_count
            ),
            "excluded_duplicate_count": (
                (
                    report.raw_duplicate_count
                    if report.raw_duplicate_count is not None
                    else report.duplicate_count
                )
                - report.duplicate_count
            ),
        }
        for report in reports
    ]
    history_records = (
        _load_history_records(Path(args.history_jsonl), root=root)
        if args.history_jsonl
        else []
    )
    trend_summary = _build_trend_summary(
        history_records=history_records,
        current_targets=target_rows,
        snapshot_date=snapshot_date,
        total_duplicate_clusters=sum(report.duplicate_count for report in reports),
    )

    payload = _build_payload(
        reports,
        snapshot_date=snapshot_date,
        exclude_module_patterns=args.exclude_module_pattern,
        exclude_actionability_categories=args.exclude_actionability_category,
        trend_summary=trend_summary,
    )
    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    _write_text(
        json_path,
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        root=root,
    )
    _write_text(
        md_path,
        _render_markdown(
            reports,
            exclude_module_patterns=tuple(args.exclude_module_pattern),
            exclude_actionability_categories=tuple(args.exclude_actionability_category),
            trend_summary=trend_summary,
            max_duplicate_clusters=args.max_duplicate_clusters,
        ),
        root=root,
    )
    if args.history_jsonl:
        _append_history_jsonl(Path(args.history_jsonl), payload=payload, root=root)

    total = sum(report.duplicate_count for report in reports)
    raw_total = sum(
        report.raw_duplicate_count
        if report.raw_duplicate_count is not None
        else report.duplicate_count
        for report in reports
    )
    print(
        "[duplication-baseline] "
        f"targets={len(reports)}; total_duplicate_clusters={total}; "
        f"total_raw_duplicate_clusters={raw_total}; "
        f"json={json_path}; markdown={md_path}"
    )
    for report in reports:
        print(
            "[duplication-baseline] "
            f"target={report.target}; duplicate_clusters={report.duplicate_count}; "
            "raw_duplicate_clusters="
            f"{report.raw_duplicate_count if report.raw_duplicate_count is not None else report.duplicate_count}"
        )
    if args.max_duplicate_clusters is not None and total > args.max_duplicate_clusters:
        print(
            "[duplication-baseline] FAIL: duplicate cluster count exceeds budget: "
            f"{total} > {args.max_duplicate_clusters}"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
