"""Shared JSON/Markdown publication for repository inventory reports."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.engineering.common.repo_paths import (
    resolve_output_path,
    write_text_confined,
)


def write_report_outputs(
    report: object,
    *,
    json_out: Path,
    md_out: Path,
    markdown: str,
    root: Path,
) -> tuple[Path, Path]:
    """Validate both destinations and prepare parents before publication."""
    json_path = resolve_output_path(json_out, root=root)
    markdown_path = resolve_output_path(md_out, root=root)
    base = root.resolve()
    for path in (json_path, markdown_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    write_text_confined(
        json_path,
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        root=root,
        allow_external_absolute=not json_path.is_relative_to(base),
    )
    write_text_confined(
        markdown_path,
        markdown,
        root=root,
        allow_external_absolute=not markdown_path.is_relative_to(base),
    )
    return json_path, markdown_path
