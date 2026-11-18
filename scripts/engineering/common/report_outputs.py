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
    """Resolve both destinations before publishing either report artifact."""
    json_path = resolve_output_path(json_out, root=root)
    markdown_path = resolve_output_path(md_out, root=root)
    write_text_confined(
        json_path,
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        root=root,
        allow_external_absolute=True,
    )
    write_text_confined(
        markdown_path,
        markdown,
        root=root,
        allow_external_absolute=True,
    )
    return json_path, markdown_path
