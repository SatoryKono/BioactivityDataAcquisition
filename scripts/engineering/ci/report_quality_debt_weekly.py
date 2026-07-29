#!/usr/bin/env python3
"""Generate weekly architecture debt report from exemptions registry."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

if __package__ in {None, ""}:
    from _compatibility_telemetry import (  # type: ignore[import-not-found]
        CompatibilitySurfaceSnapshot,
        DebtGovernanceSnapshot,
        collect_debt_governance_snapshot,
        render_debt_governance_section,
    )
else:
    from ._compatibility_telemetry import (
        CompatibilitySurfaceSnapshot,
        DebtGovernanceSnapshot,
        collect_debt_governance_snapshot,
        render_debt_governance_section,
    )

from bioetl.infrastructure.quality import (
    build_exemption_inventory,
    evaluate_debt_scorecard,
    load_debt_scorecard,
)


@dataclass(frozen=True)
class WeeklyDebtSnapshot:
    """Serializable weekly debt snapshot."""

    generated_at_utc: str
    quarter: str
    total_debt: int
    expired_debt: int
    new_debt: int
    baseline_total_debt: int
    total_budget: int
    integral_score: float
    growth_violations: int
    by_registry: dict[str, int]
    by_owner: dict[str, int]
    compatibility_surface: CompatibilitySurfaceSnapshot
    debt_governance_surface: DebtGovernanceSnapshot


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate weekly architecture debt snapshot with total/expired/new debt."
        )
    )
    parser.add_argument(
        "--registry",
        default="configs/quality/architecture_metric_exemptions.yaml",
        help="Path to architecture exemption registry YAML.",
    )
    parser.add_argument(
        "--scorecard",
        default="configs/quality/debt_scorecard.yaml",
        help="Path to debt scorecard YAML.",
    )
    parser.add_argument(
        "--json-out",
        default="reports/quality/debt-weekly.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--markdown-out",
        default="reports/quality/debt-weekly.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--summary-out",
        default="",
        help="Optional path to append a compact summary (e.g., $GITHUB_STEP_SUMMARY).",
    )
    parser.add_argument(
        "--fail-on-breach",
        action="store_true",
        help=(
            "Exit with code 1 if expired debt exists or scorecard violations are present."
        ),
    )
    return parser.parse_args()


def _build_snapshot(
    *,
    registry_path: Path,
    scorecard_path: Path,
    today: date,
) -> WeeklyDebtSnapshot:
    inventory = build_exemption_inventory(registry_path=registry_path, today=today)
    scorecard = load_debt_scorecard(scorecard_path)
    violations, evaluation = _scorecard_evaluation(
        registry_path=registry_path,
        scorecard_path=scorecard_path,
        today=today,
    )
    baseline_total = _baseline_total_debt(inventory.total_exemptions, scorecard)
    debt_governance_surface = collect_debt_governance_snapshot()
    return WeeklyDebtSnapshot(
        generated_at_utc=datetime.now(UTC).isoformat(),
        quarter=evaluation.quarter,
        total_debt=inventory.total_exemptions,
        expired_debt=inventory.expired_entries,
        new_debt=_new_debt_total(inventory.total_exemptions, baseline_total),
        baseline_total_debt=baseline_total,
        total_budget=evaluation.total_budget,
        integral_score=evaluation.integral_score,
        growth_violations=len(violations),
        by_registry=evaluation.by_registry,
        by_owner=evaluation.by_owner,
        compatibility_surface=debt_governance_surface.compatibility_surface,
        debt_governance_surface=debt_governance_surface,
    )


def _render_markdown(snapshot: WeeklyDebtSnapshot) -> str:
    return (
        "# Weekly Quality Debt Report\n\n"
        f"- Generated (UTC): `{snapshot.generated_at_utc}`\n"
        f"- Quarter: `{snapshot.quarter}`\n"
        f"- Total debt: **{snapshot.total_debt}**\n"
        f"- Expired debt: **{snapshot.expired_debt}**\n"
        f"- New debt vs baseline: **{snapshot.new_debt}**\n"
        f"- Baseline total debt: `{snapshot.baseline_total_debt}`\n"
        f"- Quarter budget: `{snapshot.total_budget}`\n"
        f"- Integral debt score: `{snapshot.integral_score}`\n"
        f"- Growth violations: `{snapshot.growth_violations}`\n\n"
        f"{_debt_governance_section(snapshot, heading='## Debt Governance Surface')}\n\n"
        "## By Registry\n\n"
        f"{_render_count_lines(snapshot.by_registry) or '- (none)'}\n\n"
        "## By Owner\n\n"
        f"{_render_count_lines(snapshot.by_owner) or '- (none)'}\n"
    )


def _scorecard_evaluation(
    *,
    registry_path: Path,
    scorecard_path: Path,
    today: date,
):
    """Return evaluated scorecard or raise when summary is unavailable."""
    violations, evaluation = evaluate_debt_scorecard(
        registry_path=registry_path,
        scorecard_path=scorecard_path,
        today=today,
    )
    if evaluation is None:
        raise ValueError("Debt scorecard evaluation failed; no summary produced.")
    return violations, evaluation


def _baseline_total_debt(current_total: int, scorecard: dict[str, object]) -> int:
    """Resolve baseline debt total from scorecard payload."""
    baseline = scorecard.get("baseline", {})
    return int(baseline.get("total_exemptions", current_total))


def _new_debt_total(current_total: int, baseline_total: int) -> int:
    """Resolve debt growth relative to baseline."""
    return max(0, current_total - baseline_total)


def _render_count_lines(counts: dict[str, int]) -> str:
    """Render simple bullet list for count mappings."""
    return "\n".join(f"- `{name}`: {count}" for name, count in counts.items())


def _compatibility_section(snapshot: WeeklyDebtSnapshot, *, heading: str) -> str:
    """Render compatibility surface section for markdown outputs."""
    return render_debt_governance_section(
        snapshot.debt_governance_surface,
        heading=heading,
    )


def _debt_governance_section(snapshot: WeeklyDebtSnapshot, *, heading: str) -> str:
    """Render unified debt-governance section for markdown outputs."""
    return render_debt_governance_section(
        snapshot.debt_governance_surface,
        heading=heading,
    )


def _write_json_report(
    path: Path, snapshot: WeeklyDebtSnapshot, *, root: Path | None = None
) -> None:
    """Write JSON debt snapshot report."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(  # NOSONAR - path confined by resolve_output_path
        json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _write_markdown_report(
    path: Path, snapshot: WeeklyDebtSnapshot, *, root: Path | None = None
) -> None:
    """Write markdown debt snapshot report."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render_markdown(snapshot), encoding="utf-8"
    )  # NOSONAR - path confined by resolve_output_path


def _write_summary_append(
    path: Path, snapshot: WeeklyDebtSnapshot, *, root: Path | None = None
) -> None:
    """Append compact summary block for CI step summary usage."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "a", encoding="utf-8"
    ) as stream:  # NOSONAR - path confined by resolve_output_path
        stream.write(
            "\n".join(
                [
                    "## Weekly Quality Debt Snapshot",
                    f"- total_debt: `{snapshot.total_debt}`",
                    f"- expired_debt: `{snapshot.expired_debt}`",
                    f"- new_debt: `{snapshot.new_debt}`",
                    f"- quarter: `{snapshot.quarter}`",
                    _debt_governance_section(
                        snapshot,
                        heading="## Debt Governance Surface Snapshot",
                    ),
                ]
            )
            + "\n"
        )


def _should_fail(args: argparse.Namespace, snapshot: WeeklyDebtSnapshot) -> bool:
    """Return True when configured breach policy should fail the run."""
    return bool(args.fail_on_breach) and (
        snapshot.expired_debt > 0 or snapshot.growth_violations > 0
    )


def main() -> int:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    args = _parse_args()
    today = date.today()
    root = REPO_ROOT

    snapshot = _build_snapshot(
        registry_path=resolve_output_path(args.registry, root=root),
        scorecard_path=resolve_output_path(args.scorecard, root=root),
        today=today,
    )
    _write_json_report(Path(args.json_out), snapshot, root=root)
    _write_markdown_report(Path(args.markdown_out), snapshot, root=root)

    if args.summary_out:
        _write_summary_append(Path(args.summary_out), snapshot, root=root)

    if _should_fail(args, snapshot):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
