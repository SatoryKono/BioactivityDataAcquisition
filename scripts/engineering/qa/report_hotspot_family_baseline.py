#!/usr/bin/env python3
"""Generate/check hotspot-family baseline artifacts for RF-06 governance."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

try:
    from scripts.engineering.qa.hotspot_family_metrics import (
        PROJECT_ROOT,
        SCORECARD_PATH,
        collect_hotspot_family_metrics,
        iter_hotspot_families,
        load_scorecard,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    try:
        # Try relative import for direct script execution
        from hotspot_family_metrics import (  # type: ignore[no-redef]
            PROJECT_ROOT,
            SCORECARD_PATH,
            collect_hotspot_family_metrics,
            iter_hotspot_families,
            load_scorecard,
        )
    except ModuleNotFoundError:
        # Try absolute import with path adjustment
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from hotspot_family_metrics import (  # type: ignore[no-redef]
            PROJECT_ROOT,
            SCORECARD_PATH,
            collect_hotspot_family_metrics,
            iter_hotspot_families,
            load_scorecard,
        )

DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "reports/quality/hotspot-family-baseline.json"
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports/quality/hotspot-family-baseline.md"
NEAR_BUDGET_RATIO = 0.8
_REVIEWED_BASELINE_METRIC_KEYS = (
    "duplication_clusters",
    "files",
    "total_loc",
    "files_ge_250_loc",
    "helper_function_ratio",
    "max_internal_fan_in",
    "max_internal_fan_in_module",
)


def _display_path(path: Path) -> str:
    """Return a stable path label for repo-local and external output paths."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _resolve_snapshot_date(scorecard: dict[str, object]) -> str:
    report_only = scorecard.get("hotspot_family_ratchets", {})
    if isinstance(report_only, dict):
        snapshot_date = report_only.get("snapshot_date")
        if isinstance(snapshot_date, str) and snapshot_date.strip():
            return snapshot_date
    return date.today().isoformat()


def _build_json_payload(
    *,
    snapshot_date: str,
    metrics: list[dict[str, object]],
) -> dict[str, object]:
    enriched_metrics = [_with_budget_warnings(family) for family in metrics]
    return {
        "summary": {
            "snapshot_date": snapshot_date,
            "families": len(enriched_metrics),
            "scorecard": str(SCORECARD_PATH.relative_to(PROJECT_ROOT)),
            "budget_warnings": sum(
                len(family.get("budget_warnings", []))
                for family in enriched_metrics
                if isinstance(family.get("budget_warnings"), list)
            ),
        },
        "families": enriched_metrics,
    }


def _budget_warnings_for_family(
    family: dict[str, object],
    *,
    warning_ratio: float = NEAR_BUDGET_RATIO,
) -> list[str]:
    """Return bounded-growth warnings before a hard budget failure."""
    budgets = family.get("bounded_growth_budgets", {})
    if not isinstance(budgets, dict):
        return []

    warnings: list[str] = []
    for metric_name, raw_budget in sorted(budgets.items()):
        raw_actual = family.get(str(metric_name))
        if (
            not isinstance(metric_name, str)
            or not isinstance(raw_budget, int)
            or raw_budget <= 0
            or not isinstance(raw_actual, int)
        ):
            continue
        if raw_actual >= raw_budget:
            state = "at_budget"
        elif raw_actual / raw_budget >= warning_ratio:
            state = "near_budget"
        else:
            continue
        warnings.append(f"{state}:{metric_name}={raw_actual}/{raw_budget}")
    return warnings


def _with_budget_warnings(family: dict[str, object]) -> dict[str, object]:
    """Return a family metrics row enriched with early budget warnings."""
    enriched = dict(family)
    enriched["budget_warnings"] = _budget_warnings_for_family(family)
    return enriched


def _merge_reviewed_baseline_metrics(
    *,
    family: dict[str, object],
    measured: dict[str, object],
) -> dict[str, object]:
    """Pin reviewed-baseline rows to the scorecard's explicit reviewed metrics.

    The hotspot-family baseline artifact is the reviewed RF-06 control surface.
    For reviewed-baseline families, the artifact must mirror the scorecard's
    locked metrics even if the current live code shape has already improved.
    Active families continue to report live measurements.
    """
    merged = dict(measured)
    if family.get("ratchet_stage") != "reviewed-baseline":
        return merged

    reviewed_metrics = family.get("metrics", {})
    if not isinstance(reviewed_metrics, dict):
        return merged

    for key in _REVIEWED_BASELINE_METRIC_KEYS:
        if key in reviewed_metrics:
            merged[key] = reviewed_metrics[key]
    return merged


def _render_markdown(
    *,
    snapshot_date: str,
    metrics: list[dict[str, object]],
) -> str:
    lines = [
        "# Hotspot Family Baseline",
        "",
        "> Generated by `python -m scripts.engineering.qa report-family-baseline`.",
        "> Use this artifact as the reviewed RF-06 family baseline for non-regression checks.",
        "",
        f"- snapshot_date: `{snapshot_date}`",
        f"- families: `{len(metrics)}`",
        "",
        (
            "| Family | Files | Total LOC | Files >=250 LOC | Helper ratio | "
            "Duplication | Max fan-in | Max fan-in module | Budgets | Budget warnings |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]

    for family in (_with_budget_warnings(item) for item in metrics):
        budgets = family.get("bounded_growth_budgets", {})
        budget_text = (
            ", ".join(f"{key}={value}" for key, value in sorted(budgets.items()))
            if isinstance(budgets, dict) and budgets
            else "-"
        )
        budget_warnings = family.get("budget_warnings", [])
        warning_text = (
            ", ".join(str(warning) for warning in budget_warnings)
            if isinstance(budget_warnings, list) and budget_warnings
            else "-"
        )
        duplication = family.get("duplication_clusters")
        duplication_text = str(duplication) if duplication is not None else "-"
        lines.append(
            "| "
            f"`{family['name']}` | "
            f"{family['files']} | "
            f"{family['total_loc']} | "
            f"{family['files_ge_250_loc']} | "
            f"{family['helper_function_ratio']:.3f} | "
            f"{duplication_text} | "
            f"{family['max_internal_fan_in']} | "
            f"`{family['max_internal_fan_in_module'] or '-'}` | "
            f"`{budget_text}` | "
            f"`{warning_text}` |"
        )

    lines.append("")
    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _check_file_sync(path: Path, expected: str) -> bool:
    if not path.exists():
        print(f"[drift] missing file: {_display_path(path)}")
        return False
    actual = path.read_text(encoding="utf-8")
    if actual == expected:
        return True
    print(f"[drift] mismatch: {_display_path(path)}")
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate/check RF-06 hotspot-family baseline artifacts."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed baseline artifacts differ from generated output.",
    )
    mode.add_argument(
        "--update",
        action="store_true",
        help="Write generated baseline artifacts to disk (default mode).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="JSON output path.",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=DEFAULT_MD_OUTPUT,
        help="Markdown output path.",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only include active hotspot families.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scorecard = load_scorecard()
    snapshot_date = _resolve_snapshot_date(scorecard)
    measured_metrics = collect_hotspot_family_metrics(
        scorecard=scorecard,
        active_only=args.active_only,
    )
    measured_by_name = {item.name: item.to_dict() for item in measured_metrics}
    metrics = [
        _merge_reviewed_baseline_metrics(
            family=family,
            measured=measured_by_name[str(family.get("name", ""))],
        )
        for family in iter_hotspot_families(
            scorecard=scorecard,
            active_only=args.active_only,
        )
        if str(family.get("name", "")) in measured_by_name
    ]
    json_payload = _build_json_payload(snapshot_date=snapshot_date, metrics=metrics)
    json_text = json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n"
    markdown = _render_markdown(snapshot_date=snapshot_date, metrics=metrics)

    if args.check:
        json_ok = _check_file_sync(args.json_output, json_text)
        md_ok = _check_file_sync(args.md_output, markdown)
        if json_ok and md_ok:
            print("[ok] hotspot-family baseline artifacts are up to date")
            return 0
        hint = "python -m scripts.engineering.qa report-family-baseline"
        if args.active_only:
            hint += " --active-only"
        hint += " --update"
        print(f"[hint] run: {hint}")
        return 1

    _write_text(args.json_output, json_text)
    _write_text(args.md_output, markdown)
    print(
        "[updated] wrote hotspot-family baseline artifacts:\n"
        f"  - {_display_path(args.json_output)}\n"
        f"  - {_display_path(args.md_output)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
