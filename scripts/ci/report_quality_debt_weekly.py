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
        collect_compatibility_surface_snapshot,
        render_compatibility_surface_section,
    )
else:
    from ._compatibility_telemetry import (
        CompatibilitySurfaceSnapshot,
        collect_compatibility_surface_snapshot,
        render_compatibility_surface_section,
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
    violations, evaluation = evaluate_debt_scorecard(
        registry_path=registry_path,
        scorecard_path=scorecard_path,
        today=today,
    )
    if evaluation is None:
        raise ValueError("Debt scorecard evaluation failed; no summary produced.")

    baseline = scorecard.get("baseline", {})
    baseline_total = int(baseline.get("total_exemptions", inventory.total_exemptions))
    new_debt = max(0, inventory.total_exemptions - baseline_total)
    compatibility_surface = collect_compatibility_surface_snapshot()

    return WeeklyDebtSnapshot(
        generated_at_utc=datetime.now(UTC).isoformat(),
        quarter=evaluation.quarter,
        total_debt=inventory.total_exemptions,
        expired_debt=inventory.expired_entries,
        new_debt=new_debt,
        baseline_total_debt=baseline_total,
        total_budget=evaluation.total_budget,
        integral_score=evaluation.integral_score,
        growth_violations=len(violations),
        by_registry=evaluation.by_registry,
        by_owner=evaluation.by_owner,
        compatibility_surface=compatibility_surface,
    )


def _render_markdown(snapshot: WeeklyDebtSnapshot) -> str:
    by_registry_lines = "\n".join(
        f"- `{name}`: {count}" for name, count in snapshot.by_registry.items()
    )
    by_owner_lines = "\n".join(
        f"- `{name}`: {count}" for name, count in snapshot.by_owner.items()
    )
    compatibility_section = render_compatibility_surface_section(
        snapshot.compatibility_surface,
        heading="## Compatibility Surface",
    )
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
        f"{compatibility_section}\n\n"
        "## By Registry\n\n"
        f"{by_registry_lines or '- (none)'}\n\n"
        "## By Owner\n\n"
        f"{by_owner_lines or '- (none)'}\n"
    )


def main() -> int:
    args = _parse_args()
    today = date.today()

    snapshot = _build_snapshot(
        registry_path=Path(args.registry),
        scorecard_path=Path(args.scorecard),
        today=today,
    )

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    markdown_path = Path(args.markdown_out)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = _render_markdown(snapshot)
    markdown_path.write_text(markdown, encoding="utf-8")

    if args.summary_out:
        summary_path = Path(args.summary_out)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n".join(
                    [
                        "## Weekly Quality Debt Snapshot",
                        f"- total_debt: `{snapshot.total_debt}`",
                        f"- expired_debt: `{snapshot.expired_debt}`",
                        f"- new_debt: `{snapshot.new_debt}`",
                        f"- quarter: `{snapshot.quarter}`",
                        render_compatibility_surface_section(
                            snapshot.compatibility_surface,
                            heading="## Compatibility Surface Snapshot",
                        ),
                    ]
                )
                + "\n"
            )

    if args.fail_on_breach and (
        snapshot.expired_debt > 0 or snapshot.growth_violations > 0
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
