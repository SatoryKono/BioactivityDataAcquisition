#!/usr/bin/env python3
"""Generate architecture debt task JSON from the exemptions registry."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from bioetl.infrastructure.quality.architecture_debt_task_generation import (
    _default_output_path,
    generate_architecture_debt_tasks_payload,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate architecture debt refactoring tasks from the exemptions registry."
        )
    )
    parser.add_argument(
        "--registry",
        default="configs/quality/architecture_metric_exemptions.yaml",
        help="Path to architecture exemptions registry YAML.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help=("Repository root used to resolve source files and default output path."),
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Explicit output path. Defaults to "
            "tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json "
            "in project root."
        ),
    )
    parser.add_argument(
        "--stdout-summary",
        action="store_true",
        help="Print the full generated JSON payload to stdout after writing the file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    generated_at = datetime.now(UTC)
    payload = generate_architecture_debt_tasks_payload(
        registry_path=args.registry,
        project_root=project_root,
        generated_at=generated_at,
    )
    output_path = (
        Path(args.output).resolve()
        if args.output is not None
        else _default_output_path(project_root=project_root, generated_at=generated_at)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = cast(dict[str, int], payload["registry_summary"])
    print(f"Generated task file: {output_path}")
    print("Registry summary:")
    for key, value in summary.items():
        print(f"  - {key}: {value}")

    task_list = cast(list[dict[str, object]], payload["tasks"])
    special_statuses = [
        task
        for task in task_list
        if task.get("status") in {"target_not_found", "not_measurable"}
    ]
    if special_statuses:
        print("Special-status tasks:")
        for task in special_statuses:
            print(f"  - {task['id']} {task['status']} {task.get('registry_key')}")

    if args.stdout_summary:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
