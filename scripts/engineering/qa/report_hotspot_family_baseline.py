#!/usr/bin/env python3
"""Generate/check hotspot-family baseline artifacts for RF-06 governance."""

from __future__ import annotations

import argparse
import json
import os
import time
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


def _display_path(path: Path) -> str:
    """Return a stable path label for repo-local and external output paths."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
            "scorecard": SCORECARD_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "budget_warnings": sum(
                len(family.get("budget_warnings", []))
                for family in enriched_metrics
                if isinstance(family.get("budget_warnings"), list)
            ),
            "budget_review_notes": sum(
                len(family.get("budget_review_notes", []))
                for family in enriched_metrics
                if isinstance(family.get("budget_review_notes"), list)
            ),
        },
        "families": enriched_metrics,
    }


def _budget_warnings_for_family(family: dict[str, object]) -> list[str]:
    """Return hard bounded-growth budget warnings for exceeded budgets."""
    budgets = family.get("bounded_growth_budgets", {})
    if not isinstance(budgets, dict):
        return []

    warnings: list[str] = []
    for metric_name, raw_budget in sorted(budgets.items()):
        raw_actual = family.get(str(metric_name))
        if (
            not isinstance(metric_name, str)
            or not isinstance(raw_budget, int)
            or raw_budget < 0
            or not isinstance(raw_actual, int)
        ):
            continue
        if raw_actual > raw_budget:
            warnings.append(f"over_budget:{metric_name}={raw_actual}/{raw_budget}")
    return warnings


def _budget_review_notes_for_family(
    family: dict[str, object],
    *,
    warning_ratio: float = NEAR_BUDGET_RATIO,
) -> list[str]:
    """Return non-blocking near/at-budget observations for reviewer context."""
    budgets = family.get("bounded_growth_budgets", {})
    if not isinstance(budgets, dict):
        return []

    notes: list[str] = []
    for metric_name, raw_budget in sorted(budgets.items()):
        raw_actual = family.get(str(metric_name))
        if (
            not isinstance(metric_name, str)
            or not isinstance(raw_budget, int)
            or raw_budget <= 0
            or not isinstance(raw_actual, int)
        ):
            continue
        if raw_actual == raw_budget:
            state = "at_budget"
        elif raw_actual / raw_budget >= warning_ratio:
            state = "near_budget"
        else:
            continue
        notes.append(f"{state}:{metric_name}={raw_actual}/{raw_budget}")
    return notes


def _with_budget_warnings(family: dict[str, object]) -> dict[str, object]:
    """Return family metrics enriched with hard warnings and review notes."""
    enriched = dict(family)
    enriched["budget_warnings"] = _budget_warnings_for_family(family)
    enriched["budget_review_notes"] = _budget_review_notes_for_family(family)
    return enriched


def _merge_reviewed_baseline_metrics(
    *,
    family: dict[str, object],
    measured: dict[str, object],
) -> dict[str, object]:
    """Return live measurements while retaining policy metadata from the family.

    Scorecard ``metrics`` rows are reviewed evidence, not a substitute for the
    current source census.  Pinning generated artifacts to those rows made
    ``--check`` incapable of detecting source regrowth while budgets still had
    headroom.  Policy fields such as ownership and bounded-growth budgets are
    already carried by ``measured``; live metrics must therefore win here.
    """
    del family
    return dict(measured)


def build_artifacts() -> tuple[dict[str, object], str]:
    """Build the live JSON payload and Markdown rendering without writing files."""
    scorecard = load_scorecard()
    snapshot_date = _resolve_snapshot_date(scorecard)
    measured_metrics = collect_hotspot_family_metrics(
        scorecard=scorecard,
        active_only=False,
    )
    measured_by_name = {item.name: item.to_dict() for item in measured_metrics}
    metrics = [
        _merge_reviewed_baseline_metrics(
            family=family,
            measured=measured_by_name[str(family.get("name", ""))],
        )
        for family in iter_hotspot_families(scorecard=scorecard)
        if str(family.get("name", "")) in measured_by_name
    ]
    return (
        _build_json_payload(snapshot_date=snapshot_date, metrics=metrics),
        _render_markdown(snapshot_date=snapshot_date, metrics=metrics),
    )


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
            "Duplication | Max fan-in | Max fan-in module | Budgets | Budget warnings | Budget review notes |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
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
        budget_review_notes = family.get("budget_review_notes", [])
        review_note_text = (
            ", ".join(str(note) for note in budget_review_notes)
            if isinstance(budget_review_notes, list) and budget_review_notes
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
            f"`{warning_text}` | "
            f"`{review_note_text}` |"
        )

    lines.append("")
    return "\n".join(lines)


def _content_already_written(path: Path, content: str) -> bool:
    if not path.exists():
        return False
    try:
        return path.read_text(encoding="utf-8") == content
    except OSError:
        return False


def _try_atomic_write(path: Path, payload: str) -> OSError | None:
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    last_error: OSError | None = None
    for attempt in range(3):
        try:
            # Avoid newline= on flaky FUSE mounts; normalize payload above.
            temporary_path.write_text(payload, encoding="utf-8")
            os.replace(temporary_path, path)
            return None
        except OSError as exc:
            last_error = exc
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass
            # Brief backoff for Google Drive / antivirus locks.
            time.sleep(0.05 * (attempt + 1))
    return last_error


def _try_direct_write(path: Path, payload: str) -> OSError | None:
    try:
        with path.open("w", encoding="utf-8") as handle:
            handle.write(payload)
        return None
    except OSError as exc:
        return exc


def _write_text(path: Path, content: str, *, root: Path | None = None) -> None:
    """Write UTF-8 text with retries for flaky WSL/Google-Drive mounts.

    Some ``/mnt/<drive>`` mounts reject certain open modes intermittently
    (``OSError: [Errno 22] Invalid argument``). Prefer atomic replace, then
    fall back to direct overwrite without the ``newline=`` kwarg.

    When ``root`` is provided (CLI path mode), confine ``path`` under that root.
    """
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if _content_already_written(path, content):
        return

    payload = content if content.endswith("\n") or content == "" else content + "\n"
    last_error = _try_atomic_write(path, payload)
    if last_error is None:
        return
    direct_error = _try_direct_write(path, payload)
    if direct_error is None:
        return
    raise OSError(
        f"Unable to write {path} after atomic and direct retries: {direct_error}"
    ) from direct_error


def _check_file_sync(path: Path, expected: str, *, root: Path | None = None) -> bool:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
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
        type=str,
        default=str(DEFAULT_JSON_OUTPUT),
        help="JSON output path.",
    )
    parser.add_argument(
        "--md-output",
        type=str,
        default=str(DEFAULT_MD_OUTPUT),
        help="Markdown output path.",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only include active hotspot families.",
    )
    return parser.parse_args()


def main() -> int:
    from scripts.engineering.common.repo_paths import resolve_output_path

    args = parse_args()
    args.json_output = resolve_output_path(args.json_output, root=PROJECT_ROOT)
    args.md_output = resolve_output_path(args.md_output, root=PROJECT_ROOT)
    if args.active_only:
        scorecard = load_scorecard()
        snapshot_date = _resolve_snapshot_date(scorecard)
        measured_metrics = collect_hotspot_family_metrics(
            scorecard=scorecard,
            active_only=True,
        )
        metrics = [item.to_dict() for item in measured_metrics]
        json_payload = _build_json_payload(
            snapshot_date=snapshot_date,
            metrics=metrics,
        )
        markdown = _render_markdown(snapshot_date=snapshot_date, metrics=metrics)
    else:
        json_payload, markdown = build_artifacts()
    json_text = json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        json_ok = _check_file_sync(args.json_output, json_text, root=PROJECT_ROOT)
        md_ok = _check_file_sync(args.md_output, markdown, root=PROJECT_ROOT)
        if json_ok and md_ok:
            print("[ok] hotspot-family baseline artifacts are up to date")
            return 0
        hint = "python -m scripts.engineering.qa report-family-baseline"
        if args.active_only:
            hint += " --active-only"
        hint += " --update"
        print(f"[hint] run: {hint}")
        return 1

    _write_text(args.json_output, json_text, root=PROJECT_ROOT)
    _write_text(args.md_output, markdown, root=PROJECT_ROOT)
    print(
        "[updated] wrote hotspot-family baseline artifacts:\n"
        f"  - {_display_path(args.json_output)}\n"
        f"  - {_display_path(args.md_output)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
