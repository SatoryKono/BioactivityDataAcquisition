"""Shared JSON/Markdown publication for repository inventory reports."""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path

from scripts.engineering.common.repo_paths import (
    resolve_output_path,
    stage_text_confined,
)


def write_report_outputs(
    report: object,
    *,
    json_out: Path,
    md_out: Path,
    markdown: str,
    root: Path,
) -> tuple[Path, Path]:
    """Prepare both report files before publishing either destination."""
    json_path = resolve_output_path(json_out, root=root)
    markdown_path = resolve_output_path(md_out, root=root)
    base = root.resolve()
    with ExitStack() as stack:
        outputs = [
            stack.enter_context(
                stage_text_confined(
                    path,
                    text,
                    root=root,
                    allow_external_absolute=not path.is_relative_to(base),
                )
            )
            for path, text in (
                (json_path, json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
                (markdown_path, markdown),
            )
        ]
        for output in outputs:
            output.publish()
    return json_path, markdown_path
