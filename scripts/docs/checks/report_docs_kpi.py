#!/usr/bin/env python3
"""Generate weekly documentation navigation KPI report.

Tracks:
  - total docs
  - docs in mkdocs nav
  - docs outside nav
  - orphan candidates (outside nav with zero inbound links)

KPI model:
  - Hard limit (blocking): docs outside nav MUST stay below/at a ceiling.
  - Target (directional): docs outside nav SHOULD converge to a lower target.
  - Orphan budget (blocking): orphan candidates MUST stay under/at threshold.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import ensure_repo_imports
else:
    from scripts.docs.checks._bootstrap import ensure_repo_imports

ensure_repo_imports()

from scripts.docs.common.markdown import (  # noqa: E402
    INLINE_CODE_RE,
    MD_LINK_RE,
    load_nav_docs,
)
from scripts.docs.common.paths import (  # noqa: E402
    DOCS_DIR,
    MKDOCS_FILE,
    PROJECT_ROOT,
    is_generated_docs_artifact,
)

ORPHAN_EXCLUDED_PREFIXES = (
    "00-project/ai/",
    "99-archive/",
    "02-architecture/diagrams/governance/00-diagramming-policy.md",
    "02-architecture/diagrams/architecture/svg/",
    "02-architecture/diagrams/architecture/png/",
    "02-architecture/diagrams/class-diagrams/svg/",
    "02-architecture/diagrams/class-diagrams/png/",
    "02-architecture/diagrams/foundation/svg/",
    "02-architecture/diagrams/foundation/png/",
    "02-architecture/diagrams/views/svg/",
    "02-architecture/diagrams/views/png/",
)
KPI_EXCLUDED_PREFIXES = (
    "reports/",
    "00-project/ai/",
)
KPI_INCLUDED_PREFIXES = ("00-project/ai/skills/global/.system/",)

DEFAULT_TARGET_NOT_IN_NAV = 120
DEFAULT_HARD_LIMIT_NOT_IN_NAV = 135
DEFAULT_MAX_ORPHANS = 0
DEFAULT_TARGET_DEADLINE = "2026-12-31"


def _safe_is_file(path: Path) -> bool:
    """Return ``False`` when path metadata cannot be read safely."""
    try:
        return path.is_file()
    except OSError:
        return False


def _safe_read_text(path: Path) -> str | None:
    """Return file contents or ``None`` when the path is unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _is_generated_docs_artifact(path: Path) -> bool:
    """Return True for generated docs artifacts that must be excluded from KPI."""
    return is_generated_docs_artifact(path, docs_root=DOCS_DIR)


@dataclass(frozen=True)
class DocsKpiMetrics:
    """Computed docs KPI metrics."""

    generated_at_utc: str
    total_docs: int
    in_nav: int
    not_in_nav: int
    orphan_candidates: int
    baseline_not_in_nav: int
    baseline_exists: bool
    not_in_nav_top_level: dict[str, int]
    orphan_top_level: dict[str, int]
    target_not_in_nav: int
    hard_limit_not_in_nav: int
    max_orphans: int
    target_deadline: str
    deadline_days_remaining: int
    status: str
    breaches: list[str]


def _load_nav_docs() -> set[str]:
    """Return markdown docs referenced by mkdocs navigation."""
    return load_nav_docs(MKDOCS_FILE)


def _collect_all_docs() -> list[Path]:
    """Return all markdown docs under docs/."""
    docs: list[Path] = []
    for path in DOCS_DIR.rglob("*.md"):
        try:
            if not _safe_is_file(path) or _is_generated_docs_artifact(path):
                continue
        except OSError:
            continue
        docs.append(path)
    return sorted(docs)


def _load_baseline_count(baseline_file: Path) -> tuple[int, bool]:
    """Return baseline count from list file."""
    if not baseline_file.exists():
        return 0, False

    baseline_text = _safe_read_text(baseline_file)
    if baseline_text is None:
        return 0, False
    lines = baseline_text.splitlines()
    entries = [
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    entries = [entry for entry in entries if _should_track_kpi_not_in_nav(entry)]
    return len(entries), True


def _should_track_kpi_not_in_nav(rel_path: str) -> bool:
    """Return True when a non-nav doc should count toward KPI backlog."""
    if rel_path.startswith(KPI_INCLUDED_PREFIXES):
        return True
    return not rel_path.startswith(KPI_EXCLUDED_PREFIXES)


def _tracked_not_in_nav_paths(not_in_nav: set[str]) -> set[str]:
    return {
        rel_path
        for rel_path in not_in_nav
        if not rel_path.startswith(ORPHAN_EXCLUDED_PREFIXES)
    }


def _resolved_docs_target(
    source: Path, raw_target: str, *, docs_root: Path
) -> str | None:
    resolved = (source.parent / raw_target).resolve()
    try:
        return resolved.relative_to(docs_root).as_posix()
    except ValueError:
        return None


def _iter_inbound_targets(source: Path, *, docs_root: Path) -> list[str]:
    targets: list[str] = []
    source_text = _safe_read_text(source)
    if source_text is None:
        return targets
    lines = source_text.splitlines()
    for line in lines:
        line_for_links = INLINE_CODE_RE.sub("", line)
        for match in MD_LINK_RE.finditer(line_for_links):
            raw_target = match.group(2).strip()
            if not raw_target or raw_target.startswith(("*", "{")):
                continue
            rel_target = _resolved_docs_target(source, raw_target, docs_root=docs_root)
            if rel_target is not None:
                targets.append(rel_target)
    return targets


def _collect_orphans(all_docs: list[Path], not_in_nav: set[str]) -> list[str]:
    """Return docs outside nav that have no inbound relative links."""
    tracked_not_in_nav = _tracked_not_in_nav_paths(not_in_nav)
    inbound = dict.fromkeys(tracked_not_in_nav, 0)
    docs_root = DOCS_DIR.resolve()

    for source in all_docs:
        for rel_target in _iter_inbound_targets(source, docs_root=docs_root):
            if rel_target in inbound:
                inbound[rel_target] += 1

    return sorted(rel for rel, count in inbound.items() if count == 0)


def _top_level_distribution(paths: list[str]) -> dict[str, int]:
    """Return top-level distribution for docs paths."""
    counter = Counter(path.split("/")[0] for path in paths)
    return dict(counter.most_common())


def _evaluate_status(
    not_in_nav_count: int,
    orphan_count: int,
    baseline_count: int,
    target_not_in_nav: int,
    hard_limit_not_in_nav: int,
    max_orphans: int,
) -> tuple[str, list[str]]:
    """Evaluate KPI status and return (status, breaches)."""
    breaches: list[str] = []

    if not_in_nav_count > hard_limit_not_in_nav:
        breaches.append(
            "hard_limit_not_in_nav_exceeded"
            f" ({not_in_nav_count} > {hard_limit_not_in_nav})"
        )
    if orphan_count > max_orphans:
        breaches.append(f"orphan_budget_exceeded ({orphan_count} > {max_orphans})")
    if baseline_count and not_in_nav_count > baseline_count:
        breaches.append(
            f"baseline_growth_detected ({not_in_nav_count} > {baseline_count})"
        )

    if breaches:
        return "breach", breaches
    if not_in_nav_count <= target_not_in_nav and orphan_count <= max_orphans:
        return "on_track", breaches
    return "monitoring", breaches


def _current_docs_state() -> tuple[list[str], list[str], set[str], list[str]]:
    all_docs = _collect_all_docs()
    nav_docs = _load_nav_docs()
    all_rel_paths = [path.relative_to(DOCS_DIR).as_posix() for path in all_docs]
    not_in_nav = sorted(
        path
        for path in all_rel_paths
        if path not in nav_docs and _should_track_kpi_not_in_nav(path)
    )
    return (
        all_rel_paths,
        nav_docs,
        set(not_in_nav),
        _collect_orphans(all_docs, set(not_in_nav)),
    )


def _deadline_days_remaining(target_deadline: date) -> int:
    today_utc = datetime.now(UTC).date()
    return (target_deadline - today_utc).days


def compute_metrics(
    baseline_file: Path,
    target_not_in_nav: int,
    hard_limit_not_in_nav: int,
    max_orphans: int,
    target_deadline: date,
) -> DocsKpiMetrics:
    """Compute docs KPI metrics for current repository state."""
    all_rel_paths, nav_docs, not_in_nav_set, orphans = _current_docs_state()
    not_in_nav = sorted(not_in_nav_set)
    baseline_count, baseline_exists = _load_baseline_count(baseline_file)
    days_remaining = _deadline_days_remaining(target_deadline)

    status, breaches = _evaluate_status(
        not_in_nav_count=len(not_in_nav),
        orphan_count=len(orphans),
        baseline_count=baseline_count,
        target_not_in_nav=target_not_in_nav,
        hard_limit_not_in_nav=hard_limit_not_in_nav,
        max_orphans=max_orphans,
    )

    return DocsKpiMetrics(
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        total_docs=len(all_rel_paths),
        in_nav=len(nav_docs),
        not_in_nav=len(not_in_nav),
        orphan_candidates=len(orphans),
        baseline_not_in_nav=baseline_count,
        baseline_exists=baseline_exists,
        not_in_nav_top_level=_top_level_distribution(not_in_nav),
        orphan_top_level=_top_level_distribution(orphans),
        target_not_in_nav=target_not_in_nav,
        hard_limit_not_in_nav=hard_limit_not_in_nav,
        max_orphans=max_orphans,
        target_deadline=target_deadline.isoformat(),
        deadline_days_remaining=days_remaining,
        status=status,
        breaches=breaches,
    )


def render_markdown(metrics: DocsKpiMetrics) -> str:
    """Render metrics as markdown report."""
    lines = [
        "# Docs KPI Weekly Report",
        "",
        f"- Generated (UTC): `{metrics.generated_at_utc}`",
        f"- Status: `{metrics.status}`",
        "",
        "## Core Metrics",
        "",
        f"- Total docs: **{metrics.total_docs}**",
        f"- In nav: **{metrics.in_nav}**",
        f"- Outside nav: **{metrics.not_in_nav}**",
        f"- Orphan candidates: **{metrics.orphan_candidates}**",
        "",
        "## KPI Thresholds",
        "",
        f"- Target outside nav (directional): `<= {metrics.target_not_in_nav}` "
        f"by `{metrics.target_deadline}` "
        f"({metrics.deadline_days_remaining} days remaining)",
        f"- Hard limit outside nav (blocking): `<= {metrics.hard_limit_not_in_nav}`",
        f"- Orphan budget (blocking): `<= {metrics.max_orphans}`",
        f"- Baseline outside nav: `{metrics.baseline_not_in_nav}` "
        f"(exists: `{metrics.baseline_exists}`)",
        "",
        "## Outside-Nav Distribution",
        "",
    ]

    for section, count in metrics.not_in_nav_top_level.items():
        lines.append(f"- `{section}`: {count}")

    lines.extend(["", "## Orphan Distribution", ""])
    if metrics.orphan_top_level:
        for section, count in metrics.orphan_top_level.items():
            lines.append(f"- `{section}`: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Breaches", ""])
    if metrics.breaches:
        for breach in metrics.breaches:
            lines.append(f"- {breach}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Generate documentation KPI report.")
    parser.add_argument(
        "--baseline-file",
        default="scripts/engineering/baselines/not_in_nav_baseline.txt",
        help="Path to not-in-nav baseline file.",
    )
    parser.add_argument(
        "--kpi-target-not-in-nav",
        type=int,
        default=DEFAULT_TARGET_NOT_IN_NAV,
        help="Directional target for docs outside nav.",
    )
    parser.add_argument(
        "--hard-limit-not-in-nav",
        type=int,
        default=DEFAULT_HARD_LIMIT_NOT_IN_NAV,
        help="Blocking limit for docs outside nav.",
    )
    parser.add_argument(
        "--max-orphans",
        type=int,
        default=DEFAULT_MAX_ORPHANS,
        help="Blocking limit for orphan candidates.",
    )
    parser.add_argument(
        "--target-deadline",
        default=DEFAULT_TARGET_DEADLINE,
        help="Target deadline date in YYYY-MM-DD format.",
    )
    parser.add_argument("--json-out", help="Write JSON report to file.")
    parser.add_argument("--markdown-out", help="Write markdown report to file.")
    parser.add_argument(
        "--summary-out",
        help="Append markdown report to summary file (for example GITHUB_STEP_SUMMARY).",
    )
    parser.add_argument(
        "--fail-on-breach",
        action="store_true",
        help="Return non-zero exit code when KPI breaches are detected.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    target_deadline = date.fromisoformat(args.target_deadline)
    baseline_file = (PROJECT_ROOT / args.baseline_file).resolve()

    metrics = compute_metrics(
        baseline_file=baseline_file,
        target_not_in_nav=args.kpi_target_not_in_nav,
        hard_limit_not_in_nav=args.hard_limit_not_in_nav,
        max_orphans=args.max_orphans,
        target_deadline=target_deadline,
    )
    markdown = render_markdown(metrics)

    if args.json_out:
        json_path = (PROJECT_ROOT / args.json_out).resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(asdict(metrics), ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.markdown_out:
        md_path = (PROJECT_ROOT / args.markdown_out).resolve()
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(markdown, encoding="utf-8")
    if args.summary_out:
        summary_path = Path(args.summary_out)
        from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

        summary_path = resolve_output_path(summary_path, root=REPO_ROOT)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(markdown)

    print(markdown, end="")

    if args.fail_on_breach and metrics.breaches:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
