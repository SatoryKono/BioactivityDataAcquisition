#!/usr/bin/env python3
"""Build an execution plan from generated architecture debt tasks."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from scripts.engineering.common.repo_paths import REPO_ROOT

from bioetl.infrastructure.quality.architecture_debt_reduction import (
    _default_plan_output_path,
    build_architecture_debt_execution_plan,
    find_latest_architecture_debt_tasks_file,
    load_architecture_debt_tasks,
)


def _portable_tasks_path(tasks_path: Path, *, project_root: Path = REPO_ROOT) -> str:
    """Return a repository-relative source identity when possible."""
    resolved_path = tasks_path.resolve(strict=False)
    resolved_root = project_root.resolve(strict=False)
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create an execution plan for architecture debt reduction from "
            "the latest tasks JSON."
        )
    )
    parser.add_argument(
        "--tasks",
        default=None,
        help=(
            "Path to tasks_architecture_metric_exemptions_*.json. Defaults to "
            "the latest file in reports/quality, with legacy root fallback."
        ),
    )
    parser.add_argument(
        "--project-root",
        default=str(REPO_ROOT),
        help="Repository root used to locate tasks and default report path.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Explicit execution-plan output path. Defaults to "
            "reports/quality/architecture_debt_execution_plan_YYYY-MM-DD-HH-MM.json."
        ),
    )
    parser.add_argument(
        "--stdout-summary",
        action="store_true",
        help="Print the full generated execution plan payload to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()

    tasks_path = (
        Path(args.tasks).resolve()
        if args.tasks is not None
        else find_latest_architecture_debt_tasks_file(project_root=project_root)
    )
    if tasks_path is None:
        parser.error(
            "No tasks_architecture_metric_exemptions_*.json files found in "
            "reports/quality. Run `python -m scripts.engineering.qa generate-debt-tasks` first."
        )

    payload = load_architecture_debt_tasks(tasks_path)
    payload["source_tasks_file"] = _portable_tasks_path(
        tasks_path,
        project_root=project_root,
    )
    generated_at = datetime.now(UTC)
    plan = build_architecture_debt_execution_plan(payload, generated_at=generated_at)
    output_path = (
        Path(args.output).resolve()
        if args.output is not None
        else _default_plan_output_path(
            project_root=project_root, generated_at=generated_at
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = cast(dict[str, object], plan["summary"])
    print(f"Execution plan file: {output_path}")
    print(f"Total tasks: {summary['total_tasks']}")
    print(f"Actionable tasks: {summary['actionable_tasks']}")
    print("Category counts:")
    for category, count in cast(dict[str, int], summary["category_counts"]).items():
        print(f"  - {category}: {count}")

    if args.stdout_summary:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
